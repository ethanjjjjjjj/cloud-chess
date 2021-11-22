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
r=redis.Redis(host='redis',port=6379)
DB_NAME = "db_name" # database name
client = MongoClient('mongodb',27017)
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
    FEN = request_data['fen'] # get fen from json
    UUID = uuid.uuid5() # generate uuid
    post = {"_id" : UUID, "fen" : FEN, "status" : "pending", "timestamp" : datetime.datetime.utcnow()} # create the item to post in the mongoDB database, with a status of pending by default
    db.posts.insert_one(post) # post the item into the database
    r.lpush(DB_NAME, UUID) # push the item into the redis queue