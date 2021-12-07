"""
Worker node for analysing a FEN taken from the Redis queue
"""

import logging
import time
import sys
import chess
import chess.engine
import redis
import pymongo
import multiprocessing

LOG_FORMAT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("chess-worker")

def main():
    redis_con = redis.Redis("redis", 6379)
    #redis_con = redis.Redis("localhost", 6379, password=os.environ("REDISPASSWORD"))
    mongo = pymongo.MongoClient("mongo", 27017)
    mongo_game_db = mongo["game"]
    fens = mongo_game_db.fens
    queue_name = "fen_analysis"
    engine1 = chess.engine.SimpleEngine.popen_uci("./stockfish14-bmi")
    engine1.configure({"Threads":multiprocessing.cpu_count()})
    try:
        while True:
            uuid = redis_con.blpop(queue_name)[1].decode("utf-8")
            logger.info("Starting work on %s", uuid)

            start = time.time()

            doc = fens.find_one({"_id": uuid})

            if doc is None:
                # Due to eventual consitency
                logger.warning("Cannot find document with uuid: %s", uuid)
                time.sleep(1) # Prevent CPU spiking
                redis_con.rpush(queue_name, uuid)
            elif doc["status"] != "pending":
                logger.warning("Recieved a uuid (%s) with non-pending status. Skipping...", uuid)
            else:
                doc["status"] = "processing"
                fens.update_one({"_id": doc["_id"]},  {"$set":doc}, True)
                fen = doc["fen"]
                board = chess.Board(fen=fen)
                #update mongo saying work in progress
                #board=chess.Board(fen=uuid)
                #board=chess.Board(fen="r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26")
                result = engine1.analyse(board, chess.engine.Limit(time=5))
                logger.info("Result of analysis is: %s", result)
                doc["result"] = str(result)
                doc["status"] = "done"
                fens.update_one({"_id": doc["_id"]}, {"$set":doc}, True)
                redis_con.rpush(uuid, str(result))
            logger.info("Done loop in %d seconds", time.time()-start)
    except Exception as e:
        print(e)
        engine1.close()

if __name__ == "__main__":
    logger.info("Starting FEN worker")
    main()
