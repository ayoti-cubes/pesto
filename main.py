from flask import Flask, redirect, request
from flask_restful import Resource, Api
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import sqlite3

# Open a connection with out sqlite database
# The check_same_thread is used here for the sake of simplicity, but it's not recommended
# to use it in production
# Its purpose is to allow the database to be accessed from multiple threads, which
# flask automatically creates for each endpoint
sqlcon = sqlite3.connect("database/sensors.db", check_same_thread=False)
cur = sqlcon.cursor()
# Create the database structure in the database file if it doesn't already exist
cur.executescript("""
CREATE TABLE IF NOT EXISTS capteurs (id_capteur TEXT PRIMARY KEY, nom TEXT);
CREATE TABLE IF NOT EXISTS releves
	(id TEXT PRIMARY KEY,
	 id_capteur TEXT,
     humidite REAL,
     temperature REAL,
     heure TEXT,
     date TEXT,
     rssi INTEGER,
     batterie INTEGER
    );
CREATE TABLE IF NOT EXISTS users
	(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nom TEXT,
      prenom TEXT,
      mail TEXT,
      password TEXT,
      droits TEXT
    );
""")
sqlcon.commit()

app = Flask(__name__, static_folder='static', static_url_path='')
api = Api(app)


# Serves the index file on the root of the domain, in order for the user
# to be able to access the web interface without appending /index.html to the URL
@app.route('/')
def root():
    return app.send_static_file('index.html')


# Sample hello world endpoint
class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}


class RemoteSensor(Resource):
    def get(self):
        # Request the remote server for the sensor data, with our API key
        response = requests.get("http://app.objco.com:8099/?account=GX1GLQRVNM&limit=6")
        dico = str(response.json())

        # The sensors ID we are looking for are in the following list
        capteurs = ["06182660", "62182233", "06190484"]

        # Initialize an empty object that is going to be used to store our newly
        # formatted sensor data
        capteursObj = {}

        # While the capteursObj is not populated, try to do the request and parsing again
        # The try expect block is helpful when the remote server is not responding
        # This usually happens overnight, so we are trying over and over again until
        # the remote server is back online and will respond to us
        while capteursObj == {}:
            try:
                # For each measurement in the response, parse the result and store
                # it in the capteursObj object
                for element in capteurs:
                    position = dico.find(element)
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    time = datetime.datetime.now().strftime("%H:%M:%S")

                    temp = str((dico[position + 14:position + 18]))
                    isanormal = (int(temp, 16) - 32768) > 0
                    isneg = (int(temp, 16) - 16384) > 0

                    if isneg:
                        temp = - (int(temp, 16) - 16384) / 10
                    else:
                        temp = int(temp, 16) / 10

                    rssi = - int(str((dico[position + 20:position + 22])), 16)

                    batterie = round((int((dico[position + 10:position + 14]), 16) / 3670) * 100, 0)

                    # Create an object with our newly formatted sensor data
                    capteursObj[element] = {
                        "temp": temp,
                        "rssi": rssi,
                        "date": date,
                        "time": time,
                        "isanormal": isanormal,
                        "isneg": isneg,
                        "batterie": batterie
                    }

                    # Checks if the sensor ID is 62182233
                    # This specific sensor doubles as a humidity sensor, and this data
                    # should be added separately from the other sensors which do not have this data
                    if element == "62182233":
                        humid = int(str((dico[position + 18:position + 20])), 16)
                        capteursObj[element]["humid"] = humid

            except Exception as e:
                print(e)
                print("Problematic request:")
                print(response)

        return capteursObj


def saveSensorData():
    # Initialize the RemoteSensor request class, to be used outside of a request
    remoteSensor = RemoteSensor()
    # Get the latest sensor data, properly formatted by our get method
    newSensorData = remoteSensor.get()
    for sensorId, sensorData in newSensorData.items():
        cur2 = sqlcon.cursor()
        # Append the sensors to the capteurs table if they're not already inside of it
        # This will permit us to assign a custom name to every sensor, that is going to
        # rely on said capteurs table to list them.
        cur2.execute(f"INSERT OR IGNORE INTO capteurs (id_capteur) VALUES ('{sensorId}')")

        cur3 = sqlcon.cursor()
        # Append the latest sensor data to the releves table, populating our measurements
        # history with new data
        cur3.execute(
            """
                REPLACE INTO releves (id, id_capteur, humidite, temperature, heure, date, rssi, batterie) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sensorId + sensorData["date"].replace('-', '') + sensorData["time"][:2],
                sensorId,
                sensorData.get("humid", None),
                sensorData["temp"],
                sensorData["time"],
                sensorData["date"],
                sensorData["rssi"],
                sensorData["batterie"]
            )
        )
        sqlcon.commit()


# Run our saveSensorData function every hour
# This will update our database with the latest sensor data
scheduler = BackgroundScheduler()
job = scheduler.add_job(saveSensorData, 'interval', minutes=60)
scheduler.start()

saveSensorData()


class SensorHistory(Resource):
    def get(self):
        cur3 = sqlcon.cursor()

        # Get all stored measurements in the database
        # sorted by date and time (descending)
        # TODO: This should be improved by only fetching a certain amount of rows
        # to prevent overflowing the database and server. Since we only want 24 rows
        # per sensor but all our sensors measurements are stored in the same table,
        # we will need to look into that.
        cur3.execute("SELECT * FROM releves ORDER BY date DESC, heure DESC")
        history = cur3.fetchall()

        outHistory = {}

        for item in history:
            if item[1] not in outHistory.keys():
                outHistory[item[1]] = []

            # Return the last 24 items for each sensor
            if len(outHistory[item[1]]) < 24:
                tempData = {
                    "id": item[0],
                    "temp": item[3],
                    "rssi": item[6],
                    "date": item[5],
                    "time": item[4],
                    "batterie": item[7],
                    "humid": item[2]
                }

                outHistory[item[1]].append(tempData)

        # The history is returned in a properly formatted object, containing a nested object
        # for every sensor. Each sensor object contains an array of the last 24 measurements
        # for that sensor.
        return outHistory


class Sensors(Resource):
    def get(self):
        cur4 = sqlcon.cursor()
        cur4.execute("SELECT * FROM capteurs")
        sensorname = cur4.fetchall()

        outName = {}

        # Get all sensors in the database, and return a properly formatted object
        # with the following structure:
        # {
        #     "SENSOR_ID"! {
        #         "nom": "SENSOR_NAME"
        #     }, ...
        # }
        for item in sensorname:
            if item[0] not in outName.keys():
                outName[item[0]] = {
                    "nom": item[1]
                }

        return outName

    def post(self):
        data = request.get_json()
        cur5 = sqlcon.cursor()

        cur5.execute("UPDATE capteurs SET nom = ? WHERE id_capteur = ?", (data["nom"], data["id"]))
        sqlcon.commit()
        return {"status": "ok"}

    def delete(self):
        data = request.get_json()
        cur6 = sqlcon.cursor()

        # Replace "nom" property by null
        cur6.execute("UPDATE capteurs SET nom = null WHERE id_capteur = ?", [data["id"]])
        sqlcon.commit()
        return {"status": "ok"}


class RegisterMethods(Resource):
    def post(self):
        # Get user data from request
        prenom = request.form['firstName']
        nom = request.form['lastName']
        password = request.form['password']
        mail = request.form['email']

        cur4 = sqlcon.cursor()
        cur4.execute("SELECT * FROM users WHERE mail = ?", [mail])
        # Check if user already exists
        if cur4.fetchone():
            return "Mail already used"
        else:
            cur4.execute("INSERT INTO users (nom, prenom, mail, password) VALUES (?, ?, ?, ?)",
                         (nom, prenom, mail, password))
        sqlcon.commit()
        return redirect('/index.html')


class UserMethods(Resource):
    def post(self):
        # Get user data from request
        mail = request.form['loginId']
        password = request.form['password']

        cur5 = sqlcon.cursor()
        cur5.execute("SELECT * FROM users WHERE mail=? AND password=?", (mail, password))

        # If there is a result with this query, the user exists in the database
        # and has provided correct information. We can then log them in.
        # TODO: Implement security token system, rather than redirecting to
        # the existing unprotected result page
        if cur5.fetchone():
            return redirect('/index.html')
        else:
            return redirect('/login.html?error=wrongUsernameOrPassword')


# Declare all routes
api.add_resource(HelloWorld, '/api/hello')
api.add_resource(RemoteSensor, '/api/currentsensor')
api.add_resource(SensorHistory, '/api/history')
api.add_resource(Sensors, '/api/sensors')
api.add_resource(RegisterMethods, '/api/register')
api.add_resource(UserMethods, '/api/login')

# Run our app on all interfaces, on port 5000
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
