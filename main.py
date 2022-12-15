from flask import Flask
from flask_restful import Resource, Api

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
