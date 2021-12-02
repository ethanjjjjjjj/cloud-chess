import logging
import os
import time
import sys

import chess.engine
import chess
import chess.pgn
import pymongo
import redis
import minio
from minio.error import S3Error

S3_HOST = os.environ.get("S3_HOST", None)
S3_ACCESS_KEY = os.environ.get("S3_ACCESS", None)
S3_SECRET_KEY = os.environ.get("S3_SECRET", None)

if S3_HOST is None or S3_ACCESS_KEY is None or S3_SECRET_KEY is None:
    print("S3_HOST, S3_ACCESS or S3_SECRET environment variable(s) not set", file=sys.stderr)
    sys.exit(1)


#launch analysis engine
engine1 = chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
#connect to redis
redis_con = redis.Redis("redis", 6379)
mongo = pymongo.MongoClient("mongo", 27017)
mongo_game_db = mongo["game"]
mongo_pgns=mongo_game_db.pgns
#connect to s3 server
s3_conn = minio.Minio(S3_HOST, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY)
found = s3_conn.bucket_exists("pgns")
while True:
    uuid=redis_con.blpop("pgn_analysis")
    document=mongo_pgns.find_one({"_id":uuid})
    
    objectid=document["objectid"]
    pgn=s3_conn.get_object("pgns",objectid)
    #check if this is in the right state to be processed
    if document["status"]=="pending":
        document["status"] = "processing"
        document["analysis"]=[]
        mongo_pgns.update_one({"_id": document["_id"]}, {"$set":document}, True)
    print(pgn)
    while pgn.readable():
        game=chess.pgn.read_game(pgn)
        gameanalysis=[]
        result=engine1.analyse(game.board(),chess.engine.Limit(depth=22))
        gameanalysis.append(result)
        while not(game.is_end()):
            game=game.next()
            result=engine1.analyse(game.board(),chess.engine.Limit(depth=22))
            gameanalysis.append(result)
        document["analysis"].append(gameanalysis)
    document["status"]="done"
    mongo_pgns.update_one({"_id":document["_id"]},{"$set":document})
