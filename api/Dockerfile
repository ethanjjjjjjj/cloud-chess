FROM python:3.9-buster
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flaskapp.py .
CMD python -u -m gunicorn -w 4 -b 0.0.0.0 flaskapp:app