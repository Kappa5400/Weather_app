import os
import requests
from flask import Flask, render_template, current_app, g, request, flash
import openmeteo_requests
import requests_cache
import click
from datetime import datetime
from retry_requests import retry
import sqlite3
from os import path



app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)
app.config['DATABASE'] = 'database.db'

ROOT = path.dirname(path.realpath(__file__))

cache_session = requests_cache.CachedSession(".cache', expires_after = 3600")
retry_session = retry(cache_session, retries = 5, backoff_factor =0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)



DATABASE = 'database.db'
db = sqlite3.connect(path.join(ROOT, 'database.db'))

def get_geo(city):

    url = f"https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city,
        "count": 1,
        "format" : "json",
        "language": "en"
    }


    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            lat = data["results"][0]["latitude"]
            long = data["results"][0]["longitude"]
            return lat, long
        else:
            ValueError(f"No results for {city}")
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def get_weather(city, lat, long):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        f"latitude": lat,
	    f"longitude": long,
	    "current" : "temperature_2m",
        "temperature_unit": "fahrenheit",
        "format": "json"
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
    if request.method == 'POST':
        city = request.form.get('city','')
        if city =='':
            flash("There is nothing in the search box!")
            return render_template('index.html')
        lat, long = get_geo(city)
        weather = get_weather(city, lat,long)
        coordinates = weather["Coordinates"]
        elevation = weather["Elevation"]
        comment = ""
        with sqlite3.connect("database.db") as cities:
            cursor = cities.cursor()
            cursor.execute(f"""SELECT exists(SELECT 1 FROM cities WHERE name="{city}");""")
            result = cursor.fetchone()
            result = result[0]
            print(result)
            print(type(result))
            if result is (0):
                cursor.execute("""
                        INSERT INTO cities (name, coordinates, elevation, comment)
                        VALUES (?, ?, ?, ?)
                    """, (city, coordinates, elevation, comment))
                cities.commit()
                db_cities = query_db("SELECT name, coordinates, elevation, comment FROM cities")
                return render_template("/data.html", cities=db_cities)
            else:
                flash(f"{city} already exists in the database!")
                return render_template("index.html")

    else:
        return render_template('index.html')

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo("Initialized the database.")

app.cli.add_command(init_db_command)

@app.route('/Chicago')
def chi():
    weather = get_weather("Chicago",42, 36)
    return render_template('city.html', city = "Chicago", weather = weather)

@app.route('/Tokyo')
def tokyo():
    weather = get_weather("Tokyo",36, 140)
    return render_template('city.html', city = "Tokyo", weather = weather)

@app.route('/data', methods=["POST", "GET"] )
def data():
    print("Start!")
    if request.method =="POST":
        print(request.form)
        delete = request.form.get("delete")
        drop = request.form.get("drop")
        comment = str(request.form.get("comment"))
        print (delete)
        print(drop)
        print(comment)

        if 'comment' in request.form and drop!= 'none' and 'delete' in request.form:
            print("Double trouble!")
            with sqlite3.connect("database.db") as cities:
                cursor = cities.cursor()
                cursor.execute(f"""UPDATE cities
                              SET comment = '{comment}'
                              WHERE name ='{drop}';""")
                cursor.execute(f"""
                            DELETE FROM cities
                           WHERE name ='{delete}';""")
                cities.commit()
            cities = query_db("SELECT name, coordinates, elevation, comment FROM cities")

            return render_template("data.html", cities=cities)

        if 'comment' in request.form and drop != 'none':
            print("Commenting!")
            with sqlite3.connect("database.db") as cities:
                cursor = cities.cursor()
                cursor.execute(f"""UPDATE cities 
                               SET comment = '{comment}' 
                               WHERE name ='{drop}';""")
                cities.commit()

        if 'delete' in request.form:
            with sqlite3.connect("database.db") as cities:
                cursor = cities.cursor()
                print("Deleting!")
                cursor.execute(f"""
                            DELETE FROM cities 
                            WHERE name ='{delete}';""")
                cities.commit()  
    print("End!")
    cities = query_db("SELECT name, coordinates, elevation, comment FROM cities")
    return render_template("data.html", cities=cities)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
