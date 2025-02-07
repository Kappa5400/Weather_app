from flask import Flask, render_template, current_app, g
import openmeteo_requests
import requests_cache
import click
from datetime import datetime
from retry_requests import retry
import sqlite3
from os import path

app = Flask(__name__)

ROOT = path.dirname(path.realpath(__file__))

cache_session = requests_cache.CachedSession(".cache', expires_after = 3600")
retry_session = retry(cache_session, retries = 5, backoff_factor =0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

DATABASE = 'database.db'
db = sqlite3.connect(path.join(ROOT, 'database.db'))

def get_geo(city):

    url = f"https://geocoding-api.open-meteo.com/v1/search{city}?name=&count=1&language=en&format=json"

    responses = openmeteo.weather_api(url)
    lat = responses.Latitude()
    long = responses.Longitude()

    return lat, long


def get_weather(city, **kwargs):
    lat = kwargs.get('lat', None)
    long = kwargs.get('long', None)

    url = "https://api.open-meteo.com/v1/forecast"

    city_dict = {
        "Chicago": {"lat": 42.0, "long" : 36.0},
        "Tokyo" : {"lat": 36.0, "long": 140.0}
    }

    if long == None:
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

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            db.commit()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


@app.route('/', methods=["POST", "GET"] )
def home():
    return render_template('index.html')

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo("Initialized the database.")

sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

@app.route('/Chicago')
def chi():
    weather = get_weather("Chicago")
    return render_template('city.html', city = "Chicago", weather = weather)

@app.route('/Tokyo')
def tokyo():
    weather = get_weather("Tokyo")
    return render_template('city.html', city = "Tokyo", weather = weather)

@app.route('/data')
def data():
    return render_template('data.html')

if __name__ == '__main__':

    app.run(debug=True)
