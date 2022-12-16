from flask import Flask
from flask_restful import Resource, Api
import requests

import sqlite3

sqlcon = sqlite3.connect("database/sensors.db")
cur = sqlcon.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS receivers (id INTEGER PRIMARY KEY, imei INT, marque_receiver TEXT);
CREATE TABLE IF NOT EXISTS capteurs (id INTEGER PRIMARY KEY, tag_info TEXT, nom TEXT);
CREATE TABLE IF NOT EXISTS releves
	(id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        for element in capteurs:
            position = dico.find(element)
            temp = str((dico[position + 14:position + 18]))
            isanormal = (int(temp, 16) - 32768) > 0
            isneg = (int(temp, 16) - 16384) > 0

            if isneg:
                 temp = - (int(temp, 16) - 16384) / 10
            else:
                 temp = int(temp, 16) / 10

            rssi = - int(str((dico[position + 20:position + 22])), 16)

            capteursObj[element] = {
                "temp": temp,
                "rssi": rssi,
                "isanormal": isanormal,
                "isneg": isneg
            }
            if element == "62182233":
                humid = int(str((dico[position + 18:position + 20]), 16))
                capteursObj[element]["humid"] = humid

        return capteursObj

api.add_resource(HelloWorld, '/api/hello')
api.add_resource(RemoteSensor, '/api/remotesensor')

if __name__ == '__main__':
    app.run(debug=True)
