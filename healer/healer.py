#every few seconds run a mongo query for everything that is pending 
# read in everything that is pending and time created was longer than 30 seconds ago
# push it to the redis queue and update the time (new id) ((?))
# r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26

import redis
import json,time
from pymongo import MongoClient
import uuid
import datetime

r=redis.Redis(host='localhost',port=6379)
DB_NAME = "work" # database name
client = MongoClient('localhost',27017)
db = client['game']

def create_dummy_entry():
    UUID = uuid.uuid4().__str__() # generate uuid
    FEN = "r5k1/pp2n1p1/5p2/2p2r1p/1P5P/1P2P3/PB4P1/1K3B1R w - - 0 26"
    fen = {"_id" : UUID, "fen" : FEN, "status" : "pending", "lastqueued" : datetime.datetime.utcnow()}
    print("dfuisbhuisdfh")
    db.fens.insert_one(fen)

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

#your_collection.find( {<< query >>} , { << fields>>} ) 
create_dummy_entry()
db.fens.find({},{})