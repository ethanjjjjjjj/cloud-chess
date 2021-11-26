# every few seconds run a mongo query for everything that is pending
# read in everything that is pending and time created was longer than 30 seconds ago
# push it to the redis queue and update the time (new id) ((?))
# r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26

import datetime
import json
import time
import uuid
import redis
from pymongo import MongoClient

r = redis.Redis(host="redis", port=6379)
DB_NAME = "work"  # database name
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
    r.rpush(DB_NAME, UUID)


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
    r.rpush(DB_NAME, UUID)


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
    r.rpush(DB_NAME, UUID)


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
    if r.llen("work") == 0:
        return False
    inQueue = False
    r.copy(DB_NAME, "new_queue")
    # items = r.lrange(DB, 0, r.llen("work")-1) # This command will return a list of items in the queue between the start point and the end point, but does this without popping
    while r.llen("work") > 0:
        uuid_ = r.blpop("new_queue")[1].decode("utf-8")
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
            uuid = db.fens.update({"_id": item["_id"]}, item)
            # push to queue
            r.rpush(DB_NAME, item["_id"])
            print("Updated item:", item)
        else:
            print("Passed item because it was still in the queue:", item)
    time.sleep(5)
    print("Loop finished; Time Elapsed = ", datetime.datetime.utcnow() - starttime)


while True:
    thirtysecs = datetime.datetime.utcnow() - datetime.timedelta(
        seconds=30
    )  # Store the time 30 seconds ago in a variable to be used for checking
    query = db.fens.find(
        {"lastqueued": {"$lt": thirtysecs}, "status": "processing"}
    )  # Query the database to find items older than 30 seconds old and with a status of "processing" (i.e. they started getting processing but did not complete within 30 sceonds, something likely crashed)
    for item in query:  # for each of these items
        item[
            "lastqueued"
        ] = (
            datetime.datetime.utcnow()
        )  # update the "lastqueued" tag to the current time
        item["status"] = "pending"

        uuid = db.fens.update(
            {"_id": item["_id"]}, item
        )  # update that item in the mongodb database
        r.rpush(DB_NAME, item["_id"])  # push the uuid to the queue
        print("Updated item:", item)  # print confirmation
    time.sleep(5)  # run this loop every 5 seconds
    print(
        "Loop finished; Time Elapsed =", datetime.datetime.utcnow() - starttime
    )  # print time elapsed for keeping track
