"""
Quart App providing a HTTP and WS access to the backend
"""

import datetime
import json
import os
import sys
import uuid
from typing import Optional

from async_timeout import timeout
import minio
from quart import abort, Quart, request, websocket
from quart_cors import cors
from pymongo import MongoClient
import redis
import requests
import chess


ANALYSIS_QUEUE = "fen_analysis"
S3_HOST = os.environ.get("S3_HOST", None)
S3_ACCESS_KEY = os.environ.get("S3_ACCESS", None)
S3_SECRET_KEY = os.environ.get("S3_SECRET", None)
PGN_BUCKET = "pgns"

if (S3_ACCESS_KEY == None) or (S3_SECRET_KEY == None):
    print("S3ACCESS or S3SECRET environment variable(s) not set", file=sys.stderr)
    sys.exit(1)


app = Quart(__name__)
cors(app)


redis_con = redis.Redis(host='redis', port=6379)
mongo_client = MongoClient('mongo', 27017)
game_db = mongo_client['game']
mongo_livegames = game_db.livegames
s3_con = minio.Minio(S3_HOST, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY,secure=False)


@app.get("/game")
async def get_game():
    """
        Allows a user to get the PGN of a game they have played
        @usage: http://localhost/game?uuid=<uuid>
    """
    game_uuid = request.args.get("uuid", None)
    if game_uuid == None:
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
    if not s3_con.bucket_exists(PGN_BUCKET):
        s3_con.make_bucket(PGN_BUCKET)

    # TODO @Ethan generate pgn_uuid for upload/ object name for upload
    pgn_uuid = str(uuid.uuid4())
    object_name = pgn_uuid + ".pgn"

    result = s3_con.put_object(PGN_BUCKET, object_name, await request.body, length=-1)

    return { "pgn_uuid": pgn_uuid }


@app.route('/fen', methods=['POST'])
async def post():
    """
    - send a json to the backend
    - the json contains the fen
    - recieve fen, take out of json into string, generate uuid
    - store both in the mongodb with a status pending
    - push into the queue
    """
    request_data = await request.get_json() # get json

    if request_data == None:
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

    # Post the item into the database
    game_db.fens.insert_one(fen_item)

    # Push the item into the redis queue
    redis_con.rpush(ANALYSIS_QUEUE, fen_uuid)

    # Wait for result from Pub/Sub
    result = redis_con.blpop(fen_uuid)[1].decode("utf-8")

    # Update database that item has been recieve
    # So that healer knows if it was lost from pub/sub failing or not
    game_db.fens.update_one({"_id": fen_uuid},  {"$set": {"status": "recieved"}}, True)

    return {"status": "ok", "data": result}


@app.websocket('/ws/bot/<game_uuid>')
async def bot_game(game_uuid = None):
    """ Allows a player to play against a bot """
    if game_uuid is None:
        game_uuid = str(uuid.uuid4())
        #initialise game by putting starting position into database
        #TODO implement storing partial pgn here while game is in play, and update with object id after fen stored as a file
        mongo_livegames.insert_one({"_id":game_uuid,"moves":[],"fen":str(chess.STARTING_FEN),"status":"pending"})
        #while true pop from queue named (gameuuid)_botmove, push player move to queue (gameuuid)_playermove, if return {"move":"",state=(draw or win)} then end connection else push next player move
        #if game is won on bot's turn, move is still sent back but client needs to know game is over
        await websocket.send(json.dumps({"type": "init", "game_uuid": game_uuid}))

    while True:
        data = json.loads(await websocket.receive())

        if data.get("type", None) == "player_move":
            app.logger.warning("Got invalid type in /ws/bot: %s", data)
            await websocket.send(json.dumps({"type": "error", "msg": "Invalid message type"}))
            continue

        if "move" not in data:
            app.logger.warning("Missing fen in ws moved type: %s", data)
            await websocket.send(json.dumps({"type": "error", "msg": "no fen on moved type"}))
            continue

        move = data["move"]
        #push gameuuid to livegames queue to signify that there has been an update, this allows any bot to calculate the next move so the game does not have to tie up one bot forever
        redis_con.rpush("livegames",json.dumps({"gameid":game_uuid,"move":move}))
        # get bot move back in form {"move":"","state":""} where state is the termination reason or ongoing, if ongoing then websocket connection can close after sending response back to the client.
        botmovejson=json.loads(str(redis_con.blpop(game_uuid)))

        game_over = False
        bot_move: Optional[str] = None
        if botmovejson["state"]!="ongoing":
            game_over=True
            if botmovejson["move"]!="":  #if game finished on bot's move
                bot_move=botmovejson["move"]
            else:
                #game finished with player's move not bot's move
                pass
        elif botmovejson["state"]=="ongoing":
            bot_move=botmovejson["move"]

        if game_over:
            await websocket.send(json.dumps({"type": "end_game", "state": botmovejson["state"], "bot_move": bot_move}))
        else:
            await websocket.send(json.dumps({"type": "bot_move", "bot_move": bot_move}))
