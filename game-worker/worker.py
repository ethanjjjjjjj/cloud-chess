import logging
import os
import time
import sys
import io
import multiprocessing
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
engine1.configure({"Threads":multiprocessing.cpu_count()})
#connect to redis
redis_con = redis.Redis("redis", 6379)
mongo = pymongo.MongoClient("mongo", 27017)
mongo_game_db = mongo["game"]
mongo_pgns=mongo_game_db.pgns
#connect to s3 server
s3_conn = minio.Minio(S3_HOST, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY,secure=False)
found = s3_conn.bucket_exists("pgns")
while True:
    game_uuid=redis_con.blpop("pgn_analysis")[1].decode("utf-8")
    print(game_uuid)
    #print(str(game_uuid))
    document=mongo_pgns.find_one({"_id":game_uuid})
    #print(document)
    #objectid=document["objectid"]
    pgn_response=s3_conn.get_object("pgns",str(game_uuid)+".pgn")
    pgn=pgn_response.data
    pgn=io.BytesIO(pgn)
    pgn=io.TextIOWrapper(pgn)
    print(type(pgn))
    #print(pgn[0:400])
    #check if this is in the right state to be processed
    if document["status"]=="pending":
        document["status"] = "processing"
        document["analysis"]=[]
        mongo_pgns.update_one({"_id": document["_id"]}, {"$set":document}, True)
    while pgn.readable():
        game=None
        game=chess.pgn.read_game(pgn)
        if game !=None:
            print("working")
            gameanalysis=[]
            result=engine1.analyse(game.board(),chess.engine.Limit(depth=10))
            gameanalysis.append(str(result))
            while not(game.is_end()):
                game=game.next()
                result=engine1.analyse(game.board(),chess.engine.Limit(depth=10))
                print(result)
                gameanalysis.append(str(result))
            document["analysis"].append(gameanalysis)
        else:
            break
    pgn_response.close()
    print("done")
    document["status"]="done"
    mongo_pgns.update_one({"_id":document["_id"]},{"$set":document})
