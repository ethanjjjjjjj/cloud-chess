"""
Flask App providing a HTTP and WS access to the backend
"""

import datetime
import logging
import uuid
import sys

from quart import abort, Quart, request
from quart_cors import cors
from pymongo import MongoClient
import redis

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger("app")

app = Quart(__name__)
cors(app)

redis_con = redis.Redis(host='redis',port=6379)
ANALYSIS_QUEUE = "fen_analysis"
mongo_client = MongoClient('mongo',27017)
game_db = mongo_client['game']


@app.route('/json-post', methods=['POST'])
async def post():
    """
    - send a json to the backend
    - the json contains the fen
    - recieve fen, take out of json into string, generate uuid
    - store both in the mongodb with a status pending
    - push into the queue
    """
    request_data = await request.get_json() # get json

    if request_data is None:
        logging.warning("Recieved an invalid request to /json-post")
        abort(400)

    if 'fen' not in request_data:
        logging.warning("Recieved a request without valid properites")
        abort(400)

    fen: str = request_data['fen'] # get fen from json
    logging.info("Client requested %s to be processed", fen)

    fen_uuid = str(uuid.uuid4()) # generate uuid

    queuetime = datetime.datetime.utcnow()
    # Item to post to mongoDB with status of pending by default
    # The time the item was queued is stored, which can be queried against as it is in the format MongoDB expects
    fen_item = {"_id": fen_uuid, "fen": fen, "status": "pending", "lastqueued": queuetime}

    game_db.fens.insert_one(fen_item) # post the item into the database
    redis_con.rpush(ANALYSIS_QUEUE, fen_uuid) # push the item into the redis queue

    # TODO wait for compuation to be completed and return it
    return "{ree: 'ree'}"
