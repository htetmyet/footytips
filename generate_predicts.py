from datetime import datetime, timedelta, timezone
import os
import requests
import pytz

api_tz = pytz.timezone("Asia/Bangkok")
local_tz = pytz.timezone("Asia/Bangkok")

def get_current_datetime_on_api_server():
    london_time = datetime.now(tz=timezone.utc).astimezone(api_tz)
    return london_time

def to_local_datetime(start_date):
    dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S")
    return api_tz.localize(dt).astimezone(local_tz)

if __name__ == "__main__":
    current_server_time = get_current_datetime_on_api_server()
    today = current_server_time.date() + timedelta(days=0)

    headers = {
        'User-Agent': 'python_requests',
        'X-RapidAPI-Key': os.environ.get('RAPIDAPI_KEY')  # Ensure this matches your environment variable name
    }

    if not headers['X-RapidAPI-Key']:
        raise ValueError("API key is not set. Please set the RAPIDAPI_KEY environment variable.")

    session = requests.Session()
    session.headers = headers

    params = {
        "iso_date": today.isoformat(),
        #"federation": "UEFA",
        "market": "classic"
    }

    prediction_endpoint = "https://football-prediction-api.p.rapidapi.com/api/v2/predictions"
    response = session.get(prediction_endpoint, params=params)

    if response.ok:
        json = response.json()
        if 'data' in json:
            json["data"].sort(key=lambda p: p["start_date"])

            for match in json["data"]:
                output = "{st} {m_id} {league}\t{ht} vs {at}\t{p} @ {odd} \t{m_stat} {m_res}"

                local_start_time = to_local_datetime(match["start_date"])
                match_id = match["id"]
                league = match["competition_name"]
                home_team = match["home_team"]
                away_team = match["away_team"]
                prediction = match["prediction"]
                prediction_odds = match.get("odds", {}).get(prediction)
                match_status = match["status"]
                match_result = match["result"]


                print(output.format(st=local_start_time, m_id=match_id, league=league,ht=home_team, at=away_team, p=prediction, odd=prediction_odds, m_stat=match_status, m_res=match_result))
        else:
            print("No data found in the response.")
    else:
        print(f"Bad response from server, status-code: {response.status_code}")
        print(response.content)
