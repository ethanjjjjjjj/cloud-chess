"""
Flask App providing a HTTP and WS access to the backend
"""

import datetime
import json
import uuid

from quart import abort, Quart, request, websocket
from quart_cors import cors
from pymongo import MongoClient
import redis
import requests


app = Quart(__name__)
cors(app)

redis_con = redis.Redis(host='redis', port=6379)
ANALYSIS_QUEUE = "fen_analysis"
mongo_client = MongoClient('mongo', 27017)
game_db = mongo_client['game']


@app.get("/game")
async def get_game():
    """
        Allows a user to get the PGN of a game they have played
        @usage: http://localhost/game?uuid=<uuid>
    """
    game_uuid = request.args.get("uuid", None)
    if game_uuid is None:
        abort(400) # Malformed request

    # TOOD get the PGN url
    # Set to None iff uuid is invalid
    pgn_url = None

    if pgn_url is None:
        abort(404) # Not found

    # Download requests in streaming mode and stream the response
    # To reduce memory use by not needing to download the entire PGN
    # file prior to sending it to the client

    pgn_request = requests.get(pgn_url, stream=True)
    async def pgn_stream():
        for line in pgn_request.iter_lines():
            yield line

    return pgn_stream()


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
        app.logger.warning("Recieved an invalid request to /json-post")
        abort(400)

    if 'fen' not in request_data:
        app.logger.warning("Recieved a request without valid properites")
        abort(400)

    fen: str = request_data['fen'] # get fen from json
    app.logger.info("Client requested %s to be processed", fen)

    fen_uuid = str(uuid.uuid4()) # generate uuid

    queuetime = datetime.datetime.utcnow()
    # Item to post to mongoDB with status of pending by default
    # The time the item was queued is stored, which can be queried against as it is in the format MongoDB expects
    fen_item = {"_id": fen_uuid, "fen": fen, "status": "pending", "lastqueued": queuetime}

    game_db.fens.insert_one(fen_item) # post the item into the database
    redis_con.rpush(ANALYSIS_QUEUE, fen_uuid) # push the item into the redis queue

    result = redis_con.blpop(fen_uuid)[1].decode("utf-8")
    return {"status": "ok", "data": result}

@app.websocket('/ws')
async def ws():
    """ Allows a player to play against a bot """
    game_type = ""
    while True:
        data = json.loads(await websocket.receive())

        if "type" not in data:
            app.logger.warning("Recieved a msg without a type field %s", data)
            continue

        if data["type"] is "start_bot":
            # Start bot
            game_type = "bot"
            pass
        elif data["type"] is "start_multi":
            # Start multi player
            game_type = "multi"
        elif data["type"] is "moved" and game_type is "bot":
            if "fen" not in data:
                app.logger.warning("Missing fen in ws moved type: %s", data)
                await websocket.send(json.dumps({"type": "error", "msg": "no fen on moved type"}))
                continue

            # TODO calc move bot should make
            # TODO calc if was best move
            new_fen = ""
            await websocket.send(json.dumps({"type": "moved", "fen": new_fen}))
        elif data["type"] is "moved" and game_type is "multi":
            # TODO send game to other player
            # TODO calc if that was best move?
            pass
