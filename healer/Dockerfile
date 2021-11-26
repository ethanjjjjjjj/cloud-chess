FROM python:3.9-buster
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY healer.py .
CMD [ "python", "./healer.py" ]