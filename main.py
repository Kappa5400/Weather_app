from flask import Flask, render_template
import openmeteo_requests
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession(".cache', expires_after = 3600")
retry_session = retry(cache_session, retries = 5, backoff_factor =0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def get_weather(city):

    city_dict = {
        "name": "Chicago" "Tokyo",
        "lat": "42" "-88",
        "long": "36" "140",
    }

    url = "https://api.open-meteo.com/v1/forecast"

    lat = 0
    long = 0

    for i in city_dict["name"]:
        if i == city:
            lat = city_dict["lat"]
            long = city_dict["long"]

    params = {
        f"latitude": lat,
	    f"longitude": long,
	    f"hourly": "temperature_2m"
    }

    responses = openmeteo.weather_api(url, params=params)

    return responses

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