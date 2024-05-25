from datetime import datetime, timedelta, timezone
import os
import requests
import pytz
import csv

api_tz = pytz.timezone("Asia/Bangkok")
local_tz = pytz.timezone("Asia/Bangkok")

def get_current_datetime_on_api_server():
    london_time = datetime.now(tz=timezone.utc).astimezone(api_tz)
    return london_time

def to_local_datetime(start_date):
    dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
    return api_tz.localize(dt).astimezone(local_tz)

if __name__ == "__main__":
    current_server_time = get_current_datetime_on_api_server()
    today = current_server_time.date()

    headers = {
        'User-Agent': 'python_requests',
        'X-RapidAPI-Key': os.environ.get('RAPIDAPI_KEY')
    }

    if not headers['X-RapidAPI-Key']:
        raise ValueError("API key is not set. Please set the RAPIDAPI_KEY environment variable.")

    session = requests.Session()
    session.headers = headers

    params = {
        "iso_date": today.isoformat(),
        "federation": "UEFA",
        "market": "classic"
    }

    prediction_endpoint = "https://football-prediction-api.p.rapidapi.com/api/v2/predictions"
    response = session.get(prediction_endpoint, params=params)

    if response.ok:
        json = response.json()
        if 'data' in json:
            json["data"].sort(key=lambda p: p["start_date"])

            with open('tmp_fix.csv', mode='w', newline='') as file:
                writer = csv.writer(file)
                for match in json["data"]:
                    local_start_time = to_local_datetime(match["start_date"])
                    match_id = match["id"]
                    league = match["competition_name"]
                    home_team = match["home_team"]
                    away_team = match["away_team"]
                    prediction = match["prediction"]
                    prediction_odds = match.get("odds", {}).get(prediction)
                    match_status = match["status"]
                    match_result = match["result"]

                    writer.writerow([local_start_time, match_id, league, home_team, away_team, prediction, prediction_odds, match_status, match_result])

            print("Data appended to tmp_fix.csv successfully.")
        else:
            print("No data found in the response.")
    else:
        print(f"Bad response from server, status-code: {response.status_code}")
        print(response.content)
