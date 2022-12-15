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
