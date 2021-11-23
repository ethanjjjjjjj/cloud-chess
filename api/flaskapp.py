from flask import Flask,jsonify,Response
from flask import request
from flask_cors import CORS
import redis
import json
import logging
import uuid
import os
import pymongo 
from pymongo import MongoClient
import datetime

app=Flask(__name__)
CORS(app)
r=redis.Redis(host='localhost',port=6379)
DB_NAME = "work" # database name
client = MongoClient('localhost',27017)
db = client['game']

"""""
- same as post but less complex? for short messages?
- thing has to be in the url
"""""
# @app.route("/GET")
# def get():
#     el = r.lpop(DB_NAME)
#     pass

"""
- send a json to the backend
- the json contains the fen
- recieve fen, take out of json into string, generate uuid
- store both in the mongodb with a status pending
- push into the queue
"""
#@app.route("/POST") # ?
@app.route('/json-post', methods=['POST'])
def post():
    request_data = request.get_json() # get json
    print(request_data)
    FEN = request_data['fen'] # get fen from json
    print(FEN)
    UUID = uuid.uuid4().__str__() # generate uuid
    #fen = {"_id" : UUID, "fen" : FEN, "status" : "pending", "timestamp" : datetime.datetime.utcnow()} # create the item to post in the mongoDB database, with a status of pending by default
    queuetime = datetime.datetime.utcnow()
    fen = {"_id" : UUID, "fen" : FEN, "status" : "pending", "lastqueued" : queuetime}   # create the item to post in the mongoDB database, with a status of pending by default
                                                                                        # The time the item was queued is stored, which can be queried against as it is in the format MongoDB expects
    db.fens.insert_one(fen) # post the item into the database
    r.rpush(DB_NAME, UUID) # push the item into the redis queue
    return "{ree:'ree'}"