from flask import Flask
from flask_restful import Resource, Api
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

api.add_resource(HelloWorld, '/api/hello')

if __name__ == '__main__':
    app.run(debug=True)

##########################################################################################################
import requests
response = requests.get("http://app.objco.com:8099/?account=GX1GLQRVNM&limit=6")
dico = str(response.json())
capteurs = ["06182660", "62182233", "06190484"]
for element in capteurs:
    position = dico.find(element)
    temp = str((dico[position + 14:position + 18]))
    rssi = str((dico[position + 20:position + 22]))
    convertion_temp = int(temp, 16)
    convertion_rssi = int(rssi, 16)
    isanormal = (convertion_temp - 32768) > 0
    isneg = (convertion_temp - 16384) > 0
    if not isanormal:
        if isneg:
            print("Température du capteur " + element, ": -" + str((convertion_temp - 16384)/10), "°C")
        else :
            print("Température du capteur " + element, ":", str(convertion_temp/10), "°C")
    else : print("Température anormale")
    if element == "62182233" :
        humid = str((dico[position + 18:position + 20]))
        convertion_humid = int(humid, 16)
        print("Humidité du capteur " + element, ":", str(convertion_humid) + "%")
    print("RSSI du capteur " + element, ": -" + str(convertion_rssi), "dBm")
