FROM docker.io/library/python:3.10-alpine

COPY requirements.txt /app/

WORKDIR /app
RUN pip install -r requirements.txt

COPY run.py /
COPY app /app/

ENV PYTHONUNBUFFERED=1

WORKDIR /

CMD [ "waitress-serve", "--port=5000", "--call", "app:create_app"]