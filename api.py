# Stdlib imports
import json
import logging

# Third-party app imports
from raven.contrib.flask import Sentry
from flask import Flask, request, jsonify
from flask.ext.cors import CORS
from flask_restful import Resource, Api, reqparse

# Setting up Flask and API
app = Flask(__name__)
api = Api(app)
CORS(app)

# Setting up parser
parser = reqparse.RequestParser()
parser.add_argument('url')


# Route to POST data for news processing
class Elastic(Resource):

    def post(self):
        args = parser.parse_args()
        print args['id']
        return jsonify({'id': res.task_id})

api.add_resource(Elastic, '/elastic')

if __name__ == "__main__":
    app.run(port=int('8000'), debug=False)
