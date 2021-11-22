#load chess engine

#connect to redis

#connect to database


#start infinite loop

# pop from work queue

# run chess engine on fen for depth 22

# export move list to database

import chess.engine
from chess.engine import *
import chess
import redis
import time
r=redis.Redis("localhost",6379)
#r=redis.Redis("localhost",6379,password=os.environ("REDISPASSWORD"))
import pymongo
from pymongo import MongoClient
m=MongoClient("localhost",27017)
mdb=m["game"]
fens=mdb.fens
engine1=chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
while True:
    uuid=r.blpop("work")[1].decode("utf-8")
    print(uuid)
    start=time.time()
    doc=fens.find_one({"_id": uuid})
    print(doc)
    fen=doc["fen"]
    board=chess.Board(fen=fen)
    #update mongo saying work in progress
    #board=chess.Board(fen=uuid)
    #board=chess.Board(fen="r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26")
    result= engine1.analyse(board,chess.engine.Limit(depth=22))
    print(result)
    doc["result"]=str(result)
    doc["status"]="done"
    uuid=fens.update({"_id":doc["_id"]},doc)
    print(time.time()-start)

print(result)
engine1.quit()
