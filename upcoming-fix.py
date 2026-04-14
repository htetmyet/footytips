import csv
import http.client
import json
import os
import socket
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from api_config import get_required_env, load_dotenv

load_dotenv()
API_KEY = get_required_env("RAPIDAPI_KEY")
API_HOST = "football-prediction-api.p.rapidapi.com"
API_TZ = ZoneInfo("Asia/Bangkok")
LOCAL_TZ = ZoneInfo("Asia/Bangkok")
FREE_FIX_FILE = "free_fix.csv"
PRE_FIX_FILE = "pre_fix.csv"
MAX_FIXTURES = 300
PRUNE_COUNT = 100
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1:11434")
OLLAMA_MODEL = "gemini-3-flash-preview:cloud"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))
OLLAMA_MAX_RETRIES = max(1, int(os.getenv("OLLAMA_MAX_RETRIES", "2")))
OLLAMA_RETRY_BACKOFF = float(os.getenv("OLLAMA_RETRY_BACKOFF", "1.5"))
RAPIDAPI_TIMEOUT = int(os.getenv("RAPIDAPI_TIMEOUT", "30"))


def get_current_api_date():
    return datetime.now(tz=timezone.utc).astimezone(API_TZ).strftime("%Y-%m-%d")


def to_local_date(start_date):
    dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
    return dt.replace(tzinfo=API_TZ).astimezone(LOCAL_TZ).date()


def transform_tips(tip, home_team, away_team):
    if tip == "1":
        return f"{home_team} wins"
    if tip == "2":
        return f"{away_team} wins"
    if tip == "12":
        return "Any team to win"
    if tip == "1X":
        return f"{home_team} wins or draw"
    if tip == "X":
        return "Draw"
    if tip == "X2":
        return f"{away_team} wins or draw"
    return tip


def fetch_matches():
    today = get_current_api_date()
    headers = {
        "User-Agent": "python_requests",
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
    }

    conn = http.client.HTTPSConnection(API_HOST, timeout=RAPIDAPI_TIMEOUT)
    params = f"/api/v2/predictions?market=classic&iso_date={today}"
    try:
        conn.request("GET", params, headers=headers)
        res = conn.getresponse()
        data = res.read()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch matches from RapidAPI (host={API_HOST}, timeout={RAPIDAPI_TIMEOUT}s): {exc}"
        ) from exc
    finally:
        conn.close()

    if res.status != 200:
        raise RuntimeError(
            f"Bad response from server, status-code: {res.status}, body: {data.decode('utf-8')}"
        )

    json_data = json.loads(data.decode("utf-8"))
    matches = json_data.get("data", [])
    matches.sort(key=lambda p: p["start_date"])
    return matches


def build_candidate_rows(matches):
    tmp_like_rows = []
    for match in matches:
        local_start_date = to_local_date(match["start_date"])
        match_id = match["id"]
        league = match["competition_name"]
        home_team = match["home_team"]
        away_team = match["away_team"]
        prediction = match["prediction"]
        prediction_odds = match.get("odds", {}).get(prediction, "N/A")
        match_status = match["status"]
        match_result = match["result"]

        tmp_like_rows.append(
            [
                local_start_date,
                match_id,
                league,
                home_team,
                away_team,
                prediction,
                prediction_odds,
                match_status,
                match_result,
            ]
        )

    # Keep only rows where the 8th column (index 7) is pending.
    return [row for row in tmp_like_rows if str(row[7]).lower() == "pending"]


def split_for_outputs(rows):
    new_data_free_fix = []
    new_data_pre_fix = []

    for row in rows:
        if not row:
            continue

        time = row[0]
        league_name = row[2]
        home_team = row[3]
        away_team = row[4]
        tips = row[5]
        try:
            odds_tips = float(row[6])
        except (ValueError, TypeError):
            odds_tips = 0.0

        new_row = [
            time,
            league_name,
            f"{home_team} vs {away_team}",
            "Predictions",
            transform_tips(tips, home_team, away_team),
            odds_tips,
            "-",
            "-",
            "now",
        ]

        if odds_tips < 1.5 and len(new_data_free_fix) < 5:
            new_data_free_fix.append(new_row)
        elif odds_tips >= 1.5 and len(new_data_pre_fix) < 5:
            new_data_pre_fix.append(new_row)

    return new_data_free_fix, new_data_pre_fix


def read_existing_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, mode="r", newline="") as file:
        return list(csv.reader(file))


def write_rows(path, rows):
    with open(path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)


def ensure_row_len(row, min_len=9):
    while len(row) < min_len:
        row.append("")


def fallback_summary(prediction_text):
    return f"Upcoming fixture tip: {prediction_text}."


def is_connectivity_or_timeout_error(exc):
    if isinstance(
        exc,
        (
            socket.timeout,
            TimeoutError,
            ConnectionError,
            OSError,
            http.client.HTTPException,
        ),
    ):
        return True

    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "timed out",
            "timeout",
            "connection refused",
            "temporarily unavailable",
            "name or service not known",
            "failed to establish a new connection",
            "remote end closed connection",
        )
    )


def generate_summary_with_ollama(matchup, prediction_text):
    prompt = (
        "Write two or three short upcoming fixture summary in plain English in professional football tipster style."
        "Maximum 25 to 30 words. No markdown, no quotes.\n"
        f"Fixture: {matchup}\n"
        f"Prediction: {prediction_text}"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}

    last_exc = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        conn = http.client.HTTPConnection(OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
        try:
            conn.request("POST", "/api/generate", body=json.dumps(payload), headers=headers)
            res = conn.getresponse()
            data = res.read()
        except Exception as exc:
            last_exc = exc
            if attempt < OLLAMA_MAX_RETRIES:
                time.sleep(OLLAMA_RETRY_BACKOFF * attempt)
                continue
            raise RuntimeError(
                f"Ollama request failed after {OLLAMA_MAX_RETRIES} attempt(s): {exc}"
            ) from exc
        finally:
            conn.close()

        if res.status != 200:
            err = RuntimeError(
                "Ollama summary request failed, "
                f"status-code: {res.status}, body: {data.decode('utf-8', errors='ignore')}"
            )
            last_exc = err
            if attempt < OLLAMA_MAX_RETRIES and res.status >= 500:
                time.sleep(OLLAMA_RETRY_BACKOFF * attempt)
                continue
            raise err

        response = json.loads(data.decode("utf-8"))
        summary = str(response.get("response", "")).strip()
        if not summary:
            raise RuntimeError("Ollama summary response was empty.")

        return " ".join(summary.split())

    raise RuntimeError(
        f"Ollama request failed after {OLLAMA_MAX_RETRIES} attempt(s): {last_exc}"
    )


def apply_upcoming_summaries(rows, summary_cache):
    updated_count = 0
    disable_ollama_for_run = False

    for row in rows:
        if not row:
            continue

        ensure_row_len(row, 9)
        if str(row[8]).strip().lower() != "now":
            continue

        matchup = str(row[2]).strip()
        prediction_text = str(row[4]).strip()
        if not matchup or not prediction_text:
            continue

        cache_key = f"{matchup}|{prediction_text}"
        if cache_key not in summary_cache:
            if disable_ollama_for_run:
                summary_cache[cache_key] = fallback_summary(prediction_text)
            else:
                try:
                    summary_cache[cache_key] = generate_summary_with_ollama(
                        matchup, prediction_text
                    )
                except Exception as exc:
                    summary_cache[cache_key] = fallback_summary(prediction_text)
                    if is_connectivity_or_timeout_error(exc):
                        disable_ollama_for_run = True
                        print(
                            "Warning: Ollama connectivity issue detected; "
                            "using fallback summaries for remaining fixtures in this run."
                        )
                    print(
                        f"Warning: using fallback summary for '{matchup}' due to Ollama error: {exc}"
                    )

        row[3] = summary_cache[cache_key]
        updated_count += 1

    return updated_count


def prune_oldest_rows_if_needed(free_rows, pre_rows):
    if len(free_rows) >= MAX_FIXTURES and len(pre_rows) >= MAX_FIXTURES:
        free_rows = free_rows[:-PRUNE_COUNT] if len(free_rows) > PRUNE_COUNT else []
        pre_rows = pre_rows[:-PRUNE_COUNT] if len(pre_rows) > PRUNE_COUNT else []
        print(
            f"Pruned oldest {PRUNE_COUNT} fixtures from both files "
            f"(totals now: {len(free_rows)} and {len(pre_rows)})."
        )

    return free_rows, pre_rows


def main():
    matches = fetch_matches()
    print(f"Number of matches retrieved: {len(matches)}")
    pending_rows = build_candidate_rows(matches)
    print(f"Pending matches selected: {len(pending_rows)}")

    new_data_free_fix, new_data_pre_fix = split_for_outputs(pending_rows)
    summary_cache = {}
    free_summaries = apply_upcoming_summaries(new_data_free_fix, summary_cache)
    pre_summaries = apply_upcoming_summaries(new_data_pre_fix, summary_cache)
    existing_data_free_fix = read_existing_rows(FREE_FIX_FILE)
    existing_data_pre_fix = read_existing_rows(PRE_FIX_FILE)

    combined_data_free_fix = new_data_free_fix + existing_data_free_fix
    combined_data_pre_fix = new_data_pre_fix + existing_data_pre_fix
    combined_data_free_fix, combined_data_pre_fix = prune_oldest_rows_if_needed(
        combined_data_free_fix, combined_data_pre_fix
    )

    write_rows(FREE_FIX_FILE, combined_data_free_fix)
    write_rows(PRE_FIX_FILE, combined_data_pre_fix)

    print(
        f"Data transformed and appended to {FREE_FIX_FILE} and {PRE_FIX_FILE} successfully."
    )
    print(
        f"Upcoming fixture summaries updated: {FREE_FIX_FILE}={free_summaries}, {PRE_FIX_FILE}={pre_summaries}"
    )


if __name__ == "__main__":
    main()
