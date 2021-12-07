"""
The healer is responsible for intoducing fault tolorance for the:
    - Worker nodes
    - The Redis Queue
    - The Redis Pub/Sub
This will re-queue/ re-publish any items which are deamed to of
gotten 'stuck' proceeding through the pipeline due to some fault
which could result from a crashed component or network error
"""
# Example FEN: r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26

import datetime
import time
import uuid
import redis
from pymongo import MongoClient
from prometheus_client import start_http_server, Summary


METRIC_FENS_FIXED =  Summary("fens_fixed", "Number of Fens fixed")

redis_con = redis.Redis(host="redis", port=6379)
ANALYSIS_QUEUE = "fen_analysis"
client = MongoClient("mongo", 27017)
db = client["game"]


def create_dummy_entry():
    UUID = uuid.uuid4().__str__()  # generate uuid
    FEN = "r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26"
    fen = {
        "_id": UUID,
        "fen": FEN,
        "status": "pending",
        "lastqueued": datetime.datetime.utcnow(),
    }
    db.fens.insert_one(fen)
    redis_con.rpush(ANALYSIS_QUEUE, UUID)


def create_dummy_entry_done():
    UUID = uuid.uuid4().__str__()  # generate uuid
    FEN = "r5k1/pp2n1p1/5sdfbsdubds4P1/1K3B1R w - - 0 26"
    fen = {
        "_id": UUID,
        "fen": FEN,
        "status": "done",
        "lastqueued": datetime.datetime.utcnow() - datetime.timedelta(seconds=60),
    }
    db.fens.insert_one(fen)
    redis_con.rpush(ANALYSIS_QUEUE, UUID)


def create_dummy_entry_processing():
    UUID = uuid.uuid4().__str__()  # generate uuid
    FEN = "r5k1/pp21R w - - 0 26"
    fen = {
        "_id": UUID,
        "fen": FEN,
        "status": "processing",
        "lastqueued": datetime.datetime.utcnow() - datetime.timedelta(seconds=60),
    }
    db.fens.insert_one(fen)
    redis_con.rpush(ANALYSIS_QUEUE, UUID)


"""
db.collectionname.find({
  "$expr":{
    "$and":[
      {"$gte":[{"$convert":{"input":"$_id","to":"date"}}, ISODate("2018-07-03T00:00:00.000Z")]},
      {"$lte":[{"$convert":{"input":"$_id","to":"date"}}, ISODate("2018-07-03T11:59:59.999Z")]}
    ]
  }
})
"""

# your_collection.find( {<< query >>} , { << fields>>} )
# thirtysecs = datetime.datetime.utcnow() - datetime.timedelta(seconds=30)
# create_dummy_entry()
# create_dummy_entry_done()
# # d = db.fens.find({'lastqueued': {"$lte:" : thirtysecs, "$gte" : datetime.datetime.utcnow()}})

# create_dummy_entry_done()
# create_dummy_entry_done()
# create_dummy_entry()
# create_dummy_entry()
# create_dummy_entry()
# create_dummy_entry()
# create_dummy_entry()
# create_dummy_entry_processing()

# #d = db.fens.find({"lastqueued": {"$lt": thirtysecs}, "status" : "pending"})
# d = db.fens.find()
# for x in d: print(x)

# old code for searching the queue for an item
# the old method was to find items that were marked as pending but no longer in the queue, i.e. something went wrong
# however searching a queue seems to be a pain, so this is (currently) not used any longer
# https://stackoverflow.com/questions/10882713/redis-list-pop-without-removing <- this has a command that can be used to search a queue without popping items
def search_queue(uuid):
    if redis_con.llen("work") == 0:
        return False
    inQueue = False
    redis_con.copy(ANALYSIS_QUEUE, "new_queue")
    # items = r.lrange(DB, 0, r.llen("work")-1) # This command will return a list of items in the queue between the start point and the end point, but does this without popping
    while redis_con.llen("work") > 0:
        uuid_ = redis_con.blpop("new_queue")[1].decode("utf-8")
        if uuid == uuid_:
            return True

    return False


starttime = datetime.datetime.utcnow()  # store starting time of process

# old code for the loop before changes were made
def old_loop():
    thirtysecs = datetime.datetime.utcnow() - datetime.timedelta(seconds=30)
    query = db.fens.find({"lastqueued": {"$lt": thirtysecs}, "status": "pending"})
    for item in query:
        # update lastqueued to now
        item["lastqueued"] = datetime.datetime.utcnow()

        if not search_queue(item["_id"]):
            db.fens.update({"_id": item["_id"]}, item)
            # push to queue
            redis_con.rpush(ANALYSIS_QUEUE, item["_id"])
            print("Updated item:", item)
        else:
            print("Passed item because it was still in the queue:", item)
    time.sleep(5)
    print("Loop finished; Time Elapsed = ", datetime.datetime.utcnow() - starttime)


def fix_work_queue() -> int:
    """
    Finds all the items in the database which have status `pending`
    and older than 30 seconds

    Returns the number of items fixed
    """
    # Store the time 30 seconds ago in a variable to be used for checking
    critical_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=30)

    # Query the database to find items older than 30 seconds old and with a status of "processing"
    # (i.e. they started getting processing but did not complete within 30 sceonds,
    #  something, either Redis or a worker, likely crashed)
    query = db.fens.find({"lastqueued": {"$lt": critical_time}, "status": "processing"})

    num_healed = 0
    for item in query:
        # update the "lastqueued" tag to the current time
        item["lastqueued"] = (datetime.datetime.utcnow())
        item["status"] = "pending"

        # update that item in the mongodb database
        db.fens.update({"_id": item["_id"]}, item)

        # push the uuid to the queue
        redis_con.rpush(ANALYSIS_QUEUE, item["_id"])
        num_healed += 1
        print("Requeued item:", item)

    METRIC_FENS_FIXED.observe(num_healed)
    return num_healed


def fix_done_pub_sub() -> int:
    """
    Finds all the items in the database which have status `done`
    and last queued more than 1.5mins ago

    Returns the number of items fixed
    """
    # Store the time 1.5 minutes ago in a variable to be used for checking
    critical_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=1, seconds=30)

    # Query the database to find items older than 30 seconds old and with a status of "done"
    # (i.e. the work was done but the request was not returned from the gateway
    # as something (Redis, probably) likely crashed)
    query = db.fens.find({"lastqueued": {"$lt": critical_time}, "status": "done"})

    num_healed = 0
    for item in query:
        # update the "lastqueued" tag to the current time
        item["lastqueued"] = (datetime.datetime.utcnow())

        # update that item in the mongodb database
        uuid = db.fens.update_one({"_id": item["_id"]}, {"$set":item})

        # push the uuid to the queue
        redis_con.rpush(uuid, str(item))
        num_healed += 1
        print("Updated item:", item)

    return num_healed


if __name__ == "__main__":
    start_http_server(5060)

    while True:
        total_queue_fixed = fix_work_queue()
        total_pub_sub_fixed = fix_done_pub_sub()

        time.sleep(5)  # run this loop every 5 seconds
        print("Loop finished; Time Elapsed =", datetime.datetime.utcnow() - starttime)
