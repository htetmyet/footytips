import http.client
import json
from datetime import datetime, timezone
import pytz
import csv

api_key = "2c85dc8beemsh376135f08c7b35fp13e565jsn14c0a12abfe2"  # Set your API key here

api_tz = pytz.timezone("Asia/Bangkok")
local_tz = pytz.timezone("Asia/Bangkok")

def get_current_datetime_on_api_server():
    return datetime.now(tz=timezone.utc).astimezone(api_tz)

def to_local_date(start_date):
    dt = datetime.strptime(start_date[:10], "%Y-%m-%d")  # Parse only the date part
    return api_tz.localize(dt).astimezone(local_tz).date()  # Convert to local date

if __name__ == "__main__":
    current_server_time = get_current_datetime_on_api_server()
    today = current_server_time.strftime("%Y-%m-%d")  # Format the date as YYYY-MM-DD

    headers = {
        'User-Agent': 'python_requests',
        'x-rapidapi-key': api_key,  # Use the directly set API key
        'x-rapidapi-host': "football-prediction-api.p.rapidapi.com"
    }

    conn = http.client.HTTPSConnection("football-prediction-api.p.rapidapi.com")
    params = f"/api/v2/predictions?market=classic&iso_date={today}"
    conn.request("GET", params, headers=headers)

    res = conn.getresponse()
    data = res.read()

    if res.status == 200:
        json_data = json.loads(data.decode("utf-8"))
        if 'data' in json_data:
            matches = json_data["data"]
            print(f"Number of matches retrieved: {len(matches)}")
            if len(matches) > 0:
                print(f"Sample match data: {matches[0]}")  # Print a sample of the match data for debugging
            matches.sort(key=lambda p: p["start_date"])

            with open('tmp_fix.csv', mode='w', newline='') as file:
                writer = csv.writer(file)
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

                    writer.writerow([local_start_date, match_id, league, home_team, away_team, prediction, prediction_odds, match_status, match_result])

            print("Data written to tmp_fix.csv successfully.")
        else:
            print("No data found in the response.")
    else:
        print(f"Bad response from server, status-code: {res.status}")
        print(data.decode("utf-8"))
