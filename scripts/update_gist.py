import os
import io
import csv
import glob
import re
import requests
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

HF_JSON_URL = (
    "https://huggingface.co/datasets/"
    "htetmyet/correct_score/resolve/main/tips/latest.json"
)

GIST_API = "https://api.github.com/gists/{}"

OUTPUT_FILENAME = "get-predict.csv"
OLD_OUTPUT_FILENAME = "old-predict.csv"


def split_match_teams(match_value):

    if not match_value:
        return "", ""

    parts = re.split(r"\s+vs\s+", match_value, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    compact_parts = re.split(r"vs", match_value, maxsplit=1, flags=re.IGNORECASE)

    if len(compact_parts) == 2:
        return compact_parts[0].strip(), compact_parts[1].strip()

    return "", ""


def map_csv_status_to_evaluation(status_value):

    value = (status_value or "").strip()

    mapping = {
        "-": "pending",
        "1": "win",
        "0": "loss"
    }

    return mapping.get(value, "")


def normalize_csv_date(date_value):

    value = (date_value or "").strip()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value.replace("-", "/")

    return value


# =========================================================
# FETCH HUGGINGFACE JSON
# =========================================================

def fetch_huggingface_json():

    print("Fetching HuggingFace JSON...")

    hf_token = os.environ.get("HF_TOKEN")

    headers = {}

    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    response = requests.get(
        HF_JSON_URL,
        headers=headers,
        timeout=30
    )

    print("HF status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    items = data.get("items", [])

    rows = []

    for item in items:

        rows.append({
            "source": "huggingface",
            "id": item.get("id", ""),
            "date": item.get("date", ""),
            "league": item.get("div", ""),
            "match": f"{item.get('team', '')} vs {item.get('opponent', '')}",
            "team": item.get("team", ""),
            "opponent": item.get("opponent", ""),
            "predicted": item.get("predicted", ""),
            "tips": item.get("tips", ""),
            "odds": item.get("odds", ""),
            "actualResult": item.get("actualResult", ""),
            "evaluationStatus": item.get("evaluationStatus", ""),
            "analysis": "",
            "result": "",
            "status": "",
            "type": "",
            "notes": item.get("notes", ""),
            "addedAt": item.get("addedAt", ""),
            "sourceFileName": item.get("sourceFileName", ""),
            "csvFile": ""
        })

    print(f"HuggingFace rows: {len(rows)}")

    return rows


# =========================================================
# FETCH CSV FILES FROM REPO
# =========================================================

def fetch_csv_files():

    print("Loading local CSV files...")

    csv_files = glob.glob("pre_fix.csv")

    print(f"CSV files found: {len(csv_files)}")

    rows = []

    for file_path in csv_files:

        print(f"Reading: {file_path}")

        try:

            with open(file_path, "r", encoding="utf-8") as f:

                reader = csv.reader(f)

                for row in reader:
                    match_value = row[2] if len(row) > 2 else ""
                    team, opponent = split_match_teams(match_value)
                    result_value = row[6] if len(row) > 6 else ""
                    status_value = row[7] if len(row) > 7 else ""
                    date_value = row[0] if len(row) > 0 else ""

                    rows.append({
                        "source": "github_csv",
                        "id": "",
                        "date": normalize_csv_date(date_value),
                        "league": row[1] if len(row) > 1 else "",
                        "match": match_value,
                        "team": team,
                        "opponent": opponent,
                        "predicted": "",
                        "tips": row[4] if len(row) > 4 else "",
                        "odds": row[5] if len(row) > 5 else "",
                        "actualResult": result_value,
                        "evaluationStatus": map_csv_status_to_evaluation(status_value),
                        "analysis": row[3] if len(row) > 3 else "",
                        "result": "",
                        "status": status_value,
                        "type": row[8] if len(row) > 8 else "",
                        "notes": "",
                        "addedAt": "",
                        "sourceFileName": "",
                        "csvFile": file_path
                    })

        except Exception as e:

            print(f"FAILED: {file_path}")
            print(e)

    print(f"CSV rows: {len(rows)}")

    return rows


# =========================================================
# MERGE
# =========================================================

def merge_rows(json_rows, csv_rows):

    merged = []

    merged.extend(json_rows)
    merged.extend(csv_rows)

    print(f"Merged rows: {len(merged)}")

    return merged


# =========================================================
# CONVERT TO CSV
# =========================================================

def rows_to_csv(rows):

    headers = [
        "source",
        "id",
        "date",
        "league",
        "match",
        "team",
        "opponent",
        "predicted",
        "tips",
        "odds",
        "actualResult",
        "evaluationStatus",
        "analysis",
        "result",
        "status",
        "type",
        "notes",
        "addedAt",
        "sourceFileName",
        "csvFile"
    ]

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=headers,
        extrasaction="ignore"
    )

    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return output.getvalue()


# =========================================================
# UPDATE GIST
# =========================================================

def update_gist(gist_id, output_filename, content):

    gist_token = os.environ.get("GIST_TOKEN")

    if not gist_token:
        raise Exception("Missing GIST_TOKEN")

    if not gist_id:
        raise Exception("Missing gist id")

    print("Updating gist...")

    url = GIST_API.format(gist_id)

    payload = {
        "files": {
            output_filename: {
                "content": content
            }
        }
    }

    headers = {
        "Authorization": f"token {gist_token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.patch(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("GitHub response:", response.status_code)

    if response.status_code >= 300:
        print(response.text)
        response.raise_for_status()

    print("Gist updated successfully")


def format_prediction_preview(rows, limit=5):
    preview_lines = []
    for i, row in enumerate(rows[:limit], start=1):
        league = (row.get("league") or "").strip()
        match = (row.get("match") or "").strip()
        tips = (row.get("tips") or "").strip()
        odds = (row.get("odds") or "").strip()
        preview_lines.append(f"{i}. {league} | {match} | Tips: {tips} | Odds: {odds}")
    if not preview_lines:
        return "No pending predictions found."
    return "\n".join(preview_lines)


def send_telegram_notification(pending_rows):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    print(f"Telegram token present: {bool(token)}; chat_id present: {bool(chat_id)}")
    if not token or not chat_id:
        print("Telegram secrets not configured, skipping notification.")
        return

    date_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    preview = format_prediction_preview(pending_rows, limit=5)
    total = len(pending_rows)

    text = (
        "⚽ *Daily Football Predictions Ready!*\n"
        f"📅 Date: {date_str}\n"
        f"📊 Total predictions: {total}\n"
        "\n"
        "*Preview*:\n"
        f"{preview}\n"
    )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, json=payload, timeout=30)
        print("Telegram response:", response.status_code)
        print("Telegram body:", response.text)
        if response.status_code >= 300:
            response.raise_for_status()
    except Exception as exc:
        print("Telegram send failed:", exc)
        raise


# =========================================================
# MAIN
# =========================================================

def main():

    print("START")

    json_rows = fetch_huggingface_json()

    csv_rows = fetch_csv_files()

    merged_rows = merge_rows(json_rows, csv_rows)

    pending_rows = []
    old_rows = []

    for row in merged_rows:
        row_type = (row.get("type") or "").strip().lower()
        if row.get("source") == "github_csv" and row_type == "old":
            old_rows.append(row)
        elif (row.get("evaluationStatus") or "").strip().lower() == "pending":
            pending_rows.append(row)
        else:
            old_rows.append(row)

    gist_id = os.environ.get("GIST_ID")
    gist_old_id = os.environ.get("GIST_OLD")

    if not gist_id:
        raise Exception("Missing GIST_ID")

    if not gist_old_id:
        raise Exception("Missing GIST_OLD")

    pending_csv_content = rows_to_csv(pending_rows)
    old_csv_content = rows_to_csv(old_rows)

    update_gist(gist_id, OUTPUT_FILENAME, pending_csv_content)
    update_gist(gist_old_id, OLD_OUTPUT_FILENAME, old_csv_content)

    send_telegram_notification(pending_rows)

    print("DONE")


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    main()
