FROM python:3.9-buster
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY stockfish14-bmi .
COPY worker.py .
CMD [ "python", "./worker.py" ]