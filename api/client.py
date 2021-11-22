import requests
import sys

URL = "http://localhost:5000/json-post"

if (len(sys.argv) <= 1): 
    raise ValueError("Specify a FEN as an argument.")
fen = sys.argv[1]

data={'fen':fen}
r= requests.post(URL, json=data)

print(r)
"""
- command line takes in a FEN
- sends to API in a post request
- will get back a response of moves
"""