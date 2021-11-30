import chess.engine
import chess
import chess.pgn
import pymongo
import redis
import time
import minio
import logging
from minio.error import S3Error

s3_access_key=os.environ("S3ACCESS")
s3_secret_key=os.environ("S3SECRET")

#launch analysis engine
engine1 = chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
#connect to redis
redis_con = redis.Redis("redis", 6379)
mongo = pymongo.MongoClient("mongo", 27017)
mongo_game_db = mongo["game"]
mongo_pgns=mongo_game_db.pgns
#connect to s3 server
s3_conn=minio.Minio("minio:9000",access_key=s3_access_key,secret_key=s3_secret_key)
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