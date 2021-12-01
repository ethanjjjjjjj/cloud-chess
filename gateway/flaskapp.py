"""
Flask App providing a HTTP and WS access to the backend
"""

import datetime
import json
import os
import sys
import uuid

from async_timeout import timeout
import minio
from quart import abort, Quart, request, websocket
from quart_cors import cors
from pymongo import MongoClient
import redis
import requests


ANALYSIS_QUEUE = "fen_analysis"
S3_HOST = os.environ.get("S3_HOST", None)
S3_ACCESS_KEY = os.environ.get("S3_ACCESS", None)
S3_SECRET_KEY = os.environ.get("S3_SECRET", None)
PGN_BUCKET = "pgns"

if S3_ACCESS_KEY is None or S3_SECRET_KEY is None:
    print("S3ACCESS or S3SECRET environment variable(s) not set", file=sys.stderr)
    sys.exit(1)


app = Quart(__name__)
cors(app)


redis_con = redis.Redis(host='redis', port=6379)
mongo_client = MongoClient('mongo', 27017)
game_db = mongo_client['game']
s3_con = minio.Minio(S3_HOST, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY)


@app.get("/game")
async def get_game():
    """
        Allows a user to get the PGN of a game they have played
        @usage: http://localhost/game?uuid=<uuid>
    """
    game_uuid = request.args.get("uuid", None)
    if game_uuid is None:
        abort(400) # Malformed request

    # TODO @Ethan how are you storing PGNs/ getting their name?
    object_name = game_uuid + ".pgn"

    pgn_url = s3_con.presigned_get_object(PGN_BUCKET, object_name, expires=datetime.timedelta(hours=1))

    # Download requests in streaming mode and stream the response
    # To reduce memory use by not needing to download the entire PGN
    # file prior to sending it to the client
    pgn_request = requests.get(pgn_url, stream=True)

    if not pgn_request.ok:
        # Bubble up error code
        abort(pgn_request.status_code)

    async def pgn_stream():
        for line in pgn_request.iter_lines():
            yield line

    return pgn_stream()


@app.post('/upload_pgn')
async def upload_game():
    async with timeout(app.config['BODY_TIMEOUT']):
        if not s3_con.bucket_exists(PGN_BUCKET):
            s3_con.make_bucket(PGN_BUCKET)

        # TODO @Ethan generate pgn_uuid for upload/ object name for upload
        pgn_uuid = ""
        object_name = pgn_uuid + ".pgn"

        result = s3_con.put_object(PGN_BUCKET, object_name, await request.body, length=-1)

        return { "pgn_uuid": pgn_uuid }


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
async def websocket_connection():
    """ Allows a player to play against a bot """
    game_type = ""
    while True:
        data = json.loads(await websocket.receive())

        if "type" not in data:
            app.logger.warning("Recieved a msg without a type field %s", data)
            continue

        if data["type"] == "start_bot":
            # Start bot
            game_type = "bot"
            pass
        elif data["type"] == "start_multi":
            # Start multi player
            game_type = "multi"
        elif data["type"] == "moved" and game_type == "bot":
            if "fen" not in data:
                app.logger.warning("Missing fen in ws moved type: %s", data)
                await websocket.send(json.dumps({"type": "error", "msg": "no fen on moved type"}))
                continue

            # TODO calc move bot should make
            # TODO calc if was best move
            new_fen = ""
            await websocket.send(json.dumps({"type": "moved", "fen": new_fen}))
        elif data["type"] == "moved" and game_type == "multi":
            # TODO send game to other player
            # TODO calc if that was best move?
            pass
