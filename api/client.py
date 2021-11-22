from flask import request, Flask
import sys

app=Flask(__name__)
URL = "localhost/json-post"

if (len(sys.argv) <= 1): 
    raise ValueError("Specify a FEN as an argument.")
fen = sys.argv[1]

data={'fen':fen}
with app.test_request_context(URL, data):
    r = request.post(URL, data)

print(r)
"""
- command line takes in a FEN
- sends to API in a post request
- will get back a response of moves
"""