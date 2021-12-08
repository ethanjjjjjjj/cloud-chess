# Cloud Computing & Big Data Course Work
Authored by: Daniel Jones, Ethan Williams, Matthew Stollery

---

## How to deploy

1) set up a container registry on a cloud platform
2) create a kubernetes cluster on the same cloud platform, make sure it can pull from the registry - we used google autopilot but any kind of kubernetes cluster should work
3) download stockfish-14 with bmi or avx2 instruction support, and place a copy in the "bot-worker", "fen-worker", and "game-worker" folders, rename to "stockfish14-bmi". For legal reasons this binary could not be included in the repo with the rest of the code.
4) build each of the images in the "bot-worker", "fen-worker", "game-worker" ,"gateway", and "healer" folders using the provided docker files. Tag the images the same name as the folder they are in.
5) push the images to the registry you set up in step one, you need to tag the images with the url of the registry to do this.
6) install helm and use it to install minio on your kubernetes cluster, make sure it is named just "minio" as other components make use of the secret called minio that it generates.
7) create a secret called s3details and create a key called S3_HOST with a value of "minio:9000" as this corresponds to the service created by the minio helm chart
8) apply each of the kubernetes manifests in the kube-manifest directory to your chosen namespace. If the pods do not start and there is an image pull backoff error then you may need to give the full url for the images within the kubernetes deployment yaml files as the kubernetes cluster you have set up is not looking at your container as the first priority.
9) good to go!

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
  - *Remember to test this on Manjaro using commands in Discord*:
    -  sudo systemctl enable docker.service
    -  sudo systemctl start docker.service
    -  sudo systemctl start docker.socket
    -  Terminal 1: docker run -it --rm -p 27017:27017 mongo
    -  Terminal 2: docker run -it --rm -p 6379:6379 redis
    -  Terminal 3: docker exec -it [redis-container-name] redis-cli
    -  Terminal 3: lpop work 1

+stollaz
