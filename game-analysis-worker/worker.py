import chess.engine
import chess
import chess.pgn
import pymongo
import redis
import time
import boto3.s3
import logging

#launch analysis engine
engine1 = chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
#connect to redis
redis_con = redis.Redis("redis", 6379)
mongo = pymongo.MongoClient("mongo", 27017)
mongo_game_db = mongo["game"]
pgns=mongo_game_db.pgns
#connect to s3 server

while True:
    redis_con.blpop("pgn_analysis")
    pgn=open("pgnfilefroms3")
    game=chess.pgn.read_game(pgn)
    result=engine1.analyse(game.board(),chess.engine.Limit(depth=22))
    print(result)
    while not(game.is_end()):
        game=game.next()
        print(game.board())
        result=engine1.analyse(game.board(),chess.engine.Limit(depth=22))
        print(result)
    
#read one game from file or all?

