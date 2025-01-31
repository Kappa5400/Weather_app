from flask import Flask, render_template
import openmeteo_requests
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession(".cache', expires_after = 3600")
retry_session = retry(cache_session, retries = 5, backoff_factor =0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def get_weather(city):

    city_dict = {
        "Chicago": {"lat": 42.0, "long" : 36.0},
        "Tokyo" : {"lat": 36.0, "long": 140.0}
    }

    url = "https://api.open-meteo.com/v1/forecast"

    lat = 0
    long = 0

    for i in city_dict:
        print(i)
        if i == city:
            lat = city_dict [i]["lat"]
            long = city_dict[i]["long"]
            break

    params = {
        f"latitude": lat,
	    f"longitude": long,
	    "current" : "temperature_2m",
        "temperature_unit": "fahrenheit"
    }

    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]

    current = response.Current()

    current_temperature_2m = current.Variables(0).Value()

    weather = {
        "Coordinates" : f"{response.Latitude()}°N {response.Longitude()}°E",
        "Elevation" : f"{response.Elevation()} m asl",
        "Timezone" : f"{response.Timezone()} {response.TimezoneAbbreviation()})",
        "Timezone difference to GMT+0" : f"{response.UtcOffsetSeconds()} s",
        "Current time" : {current.Time()},
        "Current temperature_2m" : {current_temperature_2m},
        "Hourly" : {response.Hourly}
    }

    return weather

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/Chicago')
def chi():
    weather = get_weather("Chicago")
    return render_template('city.html', city = "Chicago", weather = weather)

@app.route('/Tokyo')
def tokyo():
    weather = get_weather("Tokyo")
    return render_template('city.html', city = "Tokyo", weather = weather)

if __name__ == '__main__':
    app.run(debug=True)
