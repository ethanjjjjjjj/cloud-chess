import chess
import chess.pgn
import pymongo
import redis
import logging
import chess
import multiprocessing
import json

redis_con = redis.Redis("redis", 6379)
mongo = pymongo.MongoClient("mongo", 27017)
mongo_game_db = mongo["game"]
mongo_livegames=mongo_game_db.livegames
engine1 = chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
engine1.configure({"Threads":multiprocessing.cpu_count()})


while True:
    #game is in livegames queue if it has an update from the client, uuid and move should be pushed by the gateway
    gamejson=json.loads(redis_con.blpop("livegames")[1].decode("utf-8"))
    print(gamejson)
    gameuuid=gamejson["gameid"]
    playermove=gamejson["move"]
    #game is looked up in the database to make sure it's not finished already
    document=mongo_livegames.find_one({"_id":gameuuid})
    #varaible for the queue to push moves to
    pushqueue=gameuuid+"_botmove"
    gametype=document["type"]
    #if the game is not over
    if document["status"]=="pending":
        print("game found")
        if gametype=="bot":
            print("game type bot")
            #get last board position
            fen=document["fen"]
            #apply player move
            board=chess.Board(fen=fen)
            board.push(chess.Move.from_uci(playermove))
            #update board representation in database for next time a move is read in
            document["fen"]=board.fen()
            mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
            #check if game is over
            outcome=board.outcome()
            if outcome==None:
                result = engine1.play(board, chess.engine.Limit(time=0.1))
                botmove=result.move
                print(botmove)
                board.push(botmove)
                document["fen"]=board.fen()
                mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
                #check if game is over
                if outcome==None:
                    redis_con.rpush(gameuuid,json.dumps({"move":str(botmove),"state":"ongoing"}))
                elif outcome.termination==1:
                    redis_con.rpush(gameuuid,json.dumps({"move":str(botmove),"state":"bot_win"}))
                    document["status"]="done"
                    mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
                elif (outcome.termination>1 and outcome.termination<8) or outcome.termination==10:
                    redis_con.rpush(gameuuid,json.dumps({"move":str(botmove),"state":"draw"}))
                    document["status"]="done"
                    mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
                elif outcome.termination==8 or outcome.termination==9:
                    print("variant win/loss")
                else:
                    print("unknown termination")
            elif outcome.termination==1:
                redis_con.rpush(gameuuid,json.dumps({"move":"","state":"player_win"}))
                document["status"]="done"
                mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
            elif (outcome.termination>1 and outcome.termination<8) or outcome.termination==10:
                redis_con.rpush(gameuuid,json.dumps({"move":"","state":"draw"}))
                document["status"]="done"
                mongo_livegames.update_one({"_id": document["_id"]},  {"$set":document}, True)
            elif outcome.termination==8 or outcome.termination==9:
                print("variant win/loss")
            else:
                print("unknown termination")
                


        elif gametype=="player":
            print("game type player")
            print("not implemented yet")
        else:
            print("invalid game type")
    
