
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import timedelta
from sqlalchemy.testing import db
from sqlalchemy.orm import DeclarativeBase

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite"
app.secret_key = "hello"
app.config['SQALCHEMY_DATABASE_URI'] = 'sqlite:///cities.sqlite3'
app.config["SQALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(minutes=5)
db.init_app(app)

cache_session = requests_cache.CachedSession(".cache', expires_after = 3600")
retry_session = retry(cache_session, retries = 5, backoff_factor =0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

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

class cities(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    city = db.Column("city", db.String(20))
    coordinates = db.Column('coordinates', db.string(20))
    elevation = db.Column("elevation", db.string(20))

    def __init__(self, city, coordinates, elevation):
        self.city = city
        self.coordinates = coordinates
        self.elevation = elevation

@app.route('/', methods=["POST", "GET"] )
def home():
    city = None
    if "city" in session:
        city = session["city"]
    if request.method == "POST":
        city = request.form["city"]
        session["city"] = city

        found_city = cities.query.filter_by(city=city).first()
        if found_city:
            session["city"] = found_city.city
        else:
            lat, long = get_geo(city)
            get_weather(city,lat,long)
            city = cities(city, )
            db.commit()

        flash("Added!")
    else:
        if "city" in session:
            city = session["city"]
    return render_template('data.html', city=city)


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True  # <--- makes the permanent session
        user = request.form["nm"]
        session["user"] = user
        flash("Login Succeseful!")
        return redirect(url_for("user"))
    else:
        if "user" in session:
            flash("Already Logged In!")
            return redirect(url_for("user"))

        return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/<usr>")
def user(usr):
    return f"<h1>Hi {usr}.</h1<a href="/">Go back</a>"



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
    db.create_all()
    app.run(debug=True)
