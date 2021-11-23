# Cloud Computing & Big Data Course Work
Authored by: Daniel Jones, Ethan Williams, Matthew Stollery

---
## Materials

[Prompt Link](CW_Description.pdf)

[LNCS Guide Stuff](https://www.springer.com/gp/computer-science/lncs/conference-proceedings-guidelines)

[UCI Engine Communication](https://python-chess.readthedocs.io/en/v0.14.0/uci.html)

[Stockfish](https://stockfishchess.org/)

[FEN Wiki](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation)

[PGN Parsing and Writing](https://python-chess.readthedocs.io/en/latest/pgn.html)

[Redis with Python](https://docs.redis.com/latest/rs/references/client_references/client_python/)

[Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

[MongoDB](https://www.w3schools.com/python/python_mongodb_getstarted.asp)

[MongoDB Tutorial](https://pymongo.readthedocs.io/en/stable/tutorial.html)

[Build and Deploy with Flask](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/python)

[Flask-Cors](https://pypi.org/project/Flask-Cors/)

[Flask Quickstart](https://flask.palletsprojects.com/en/2.0.x/quickstart/)

[HTTP Methods](https://www.w3schools.com/tags/ref_httpmethods.asp)

---
## TODO
### In_Progress Branch
- healer.py
  - Fix the `searchQueue()` function, as currently it never returns True as it never finds matching UUIDs
  - I have just realised that this is at least partially because I forgot the loop...
    - This should be `while r.llen("work") > 0:` it should pop items and check the id
  - It may also be something to do with the copying of the queue into a new name - more testing is needed
  - The database component works though, just the queue part needs testing
