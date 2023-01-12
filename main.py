from flask import Flask, redirect, request
from flask_restful import Resource, Api
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import sqlite3

sqlcon = sqlite3.connect("database/sensors.db", check_same_thread=False)
cur = sqlcon.cursor()
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

@app.route('/')
def root():
    return app.send_static_file('index.html')

class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

class RemoteSensor(Resource):
    def get(self):
        response = requests.get("http://app.objco.com:8099/?account=GX1GLQRVNM&limit=6")
        dico = str(response.json())
        capteurs = ["06182660", "62182233", "06190484"]
        capteursObj = {}

        while capteursObj == {}:
            try:
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

                    capteursObj[element] = {
                        "temp": temp,
                        "rssi": rssi,
                        "date": date,
                        "time": time,
                        "isanormal": isanormal,
                        "isneg": isneg,
                        "batterie": batterie
                    }

                    if element == "62182233":
                        humid = int(str((dico[position + 18:position + 20])), 16)
                        capteursObj[element]["humid"] = humid

            except Exception as e:
                print(e)
                print("Problematic request:")
                print(response)

        return capteursObj

def saveSensorData():
    remoteSensor = RemoteSensor()
    newSensorData = remoteSensor.get()
    for sensorId, sensorData in newSensorData.items():
        cur2 = sqlcon.cursor()
        cur2.execute(f"INSERT OR IGNORE INTO capteurs (id_capteur) VALUES ('{sensorId}')")

        cur3 = sqlcon.cursor()
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

scheduler = BackgroundScheduler() #run saveSensorData every 60 minutes
job = scheduler.add_job(saveSensorData, 'interval', minutes=60)
scheduler.start()

saveSensorData()

class SensorHistory(Resource):
    def get(self):
        cur3 = sqlcon.cursor()
        cur3.execute("SELECT * FROM releves ORDER BY date DESC, heure DESC")
        history = cur3.fetchall()

        outHistory = {}

        for item in history:
            if item[1] not in outHistory.keys():
                outHistory[item[1]] = []

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

        return outHistory

class Sensors(Resource):
    def get(self):
        cur4 = sqlcon.cursor()
        cur4.execute("SELECT * FROM capteurs")
        sensorname = cur4.fetchall()

        outName = {}

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
        cur6.execute("UPDATE capteurs SET nom = null WHERE id_capteur = ?", (data["id"]))
        sqlcon.commit()
        return {"status": "ok"}

@app.route('/api/register', methods=['POST'])
def CreateAccount():
    prenom = request.form['firstName']
    nom = request.form['lastName']
    password = request.form['password']
    mail = request.form['email']
    
    cur4 = sqlcon.cursor()
    cur4.execute("SELECT * FROM users WHERE mail = ?", (mail))
    if cur4.fetchone():
        return "Mail already used"
    else:
        cur4.execute("INSERT INTO users (nom, prenom, mail, password) VALUES (?, ?, ?, ?)", (nom, prenom, mail, password))
    sqlcon.commit()
    return redirect('/index.html')

@app.route('/api/login', methods=['POST'])
def login():
    mail = request.form['loginId']
    password = request.form['password']

    cur5 = sqlcon.cursor()
    cur5.execute("SELECT * FROM users WHERE mail=? AND password=?", (mail, password))
    if cur5.fetchone():
        return redirect('/index.html')
    else:
        return "Identifiant ou mot de passe inconnu merci de bien vouloir réessayer."

api.add_resource(HelloWorld, '/api/hello')
api.add_resource(RemoteSensor, '/api/currentsensor')
api.add_resource(SensorHistory, '/api/history')
api.add_resource(Sensors, '/api/sensors')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
