"""
Flask App providing a HTTP and WS access to the backend
"""

import datetime
import logging
import uuid
import sys

from flask import abort, Flask, request
from flask_cors import CORS
from pymongo import MongoClient
import redis

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger("app")

app=Flask(__name__)
CORS(app)

r=redis.Redis(host='localhost', port=6379)
DB_NAME = "work" # database name
client = MongoClient('localhost', 27017)
db = client['game']


@app.route('/json-post', methods=['POST'])
def post():
    """
    - send a json to the backend
    - the json contains the fen
    - recieve fen, take out of json into string, generate uuid
    - store both in the mongodb with a status pending
    - push into the queue
    """
    request_data = request.get_json() # get json

    if request_data is None:
        logging.warning("Recieved an invalid request to /json-post")
        abort(400)

    print(request_data)
    if 'fen' not in request_data:
        logging.warning("Recieved a request without valid properites")
        abort(400)

    fen = request_data['fen'] # get fen from json
    logging.info("Client requested %s to be processed", fen)

    fen_uuid = str(uuid.uuid4()) # generate uuid

    queuetime = datetime.datetime.utcnow()
    # Item to post to mongoDB with status of pending by default
    # The time the item was queued is stored, which can be queried against as it is in the format MongoDB expects
    fen = {"_id": fen_uuid, "fen": fen, "status": "pending", "lastqueued": queuetime}

    db.fens.insert_one(fen) # post the item into the database
    r.rpush(DB_NAME, fen_uuid) # push the item into the redis queue
    return "{ree:'ree'}"
