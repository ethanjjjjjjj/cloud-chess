from flask import request
import sys

URL = "localhost/json-post"

if (len(sys.argv) <= 1): 
    raise ValueError("Specify a FEN as an argument.")
fen = sys.argv[1]

r = request.post(URL, data = {'fen' : fen})

print(r)
"""
- command line takes in a FEN
- sends to API in a post request
- will get back a response of moves
"""