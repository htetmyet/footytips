import csv
import http.client
import json

from api_config import get_required_env, load_dotenv

load_dotenv()
API_KEY = get_required_env("RAPIDAPI_KEY")
API_HOST = "football-prediction-api.p.rapidapi.com"
FREE_FIX_FILE = "free_fix.csv"
PRE_FIX_FILE = "pre_fix.csv"
MARKET = "classic"


def fetch_predictions_by_date(iso_date, cache):
    if iso_date in cache:
        return cache[iso_date]

    headers = {
        "User-Agent": "python_requests",
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
    }

    conn = http.client.HTTPSConnection(API_HOST)
    params = f"/api/v2/predictions?market={MARKET}&iso_date={iso_date}"
    conn.request("GET", params, headers=headers)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        raise RuntimeError(
            f"Bad response for {iso_date}, status-code: {res.status}, body: {data.decode('utf-8')}"
        )

    payload = json.loads(data.decode("utf-8"))
    matches = payload.get("data", [])
    cache[iso_date] = matches
    return matches


def ensure_row_len(row, min_len=9):
    while len(row) < min_len:
        row.append("")


def split_matchup(matchup):
    parts = matchup.split(" vs ", 1)
    if len(parts) != 2:
        return None, None
    return parts[0].strip(), parts[1].strip()


def status_to_score(status):
    if status == "won":
        return "1"
    if status == "lost":
        return "0"
    return None


def find_api_match(row, predictions):
    row_date = row[0].strip()
    row_competition = row[1].strip()
    home_team, away_team = split_matchup(row[2].strip())
    if not home_team or not away_team:
        return None

    for item in predictions:
        api_date = str(item.get("start_date", ""))[:10]
        if api_date != row_date:
            continue
        if str(item.get("competition_name", "")).strip() != row_competition:
            continue
        if str(item.get("market", "")).strip() != MARKET:
            continue
        if str(item.get("home_team", "")).strip() != home_team:
            continue
        if str(item.get("away_team", "")).strip() != away_team:
            continue
        return item

    return None


def update_file(path, cache):
    with open(path, mode="r", newline="") as file:
        rows = list(csv.reader(file))

    updated_count = 0
    for row in rows:
        if not row:
            continue

        ensure_row_len(row, 9)
        if row[8].strip().lower() != "now":
            continue

        iso_date = row[0].strip()
        predictions = fetch_predictions_by_date(iso_date, cache)
        item = find_api_match(row, predictions)
        if not item:
            continue

        status = str(item.get("status", "")).strip().lower()
        score = status_to_score(status)
        if score is None:
            continue

        row[6] = str(item.get("result", row[6]))
        row[7] = score
        row[8] = "old"
        updated_count += 1

    with open(path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)

    return updated_count


def main():
    cache = {}
    free_updated = update_file(FREE_FIX_FILE, cache)
    pre_updated = update_file(PRE_FIX_FILE, cache)
    print(
        f"Updated rows: {FREE_FIX_FILE}={free_updated}, {PRE_FIX_FILE}={pre_updated}"
    )


if __name__ == "__main__":
    main()
