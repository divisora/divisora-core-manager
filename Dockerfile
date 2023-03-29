FROM docker.io/library/python:3.10-alpine

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY app /app/

ENV PYTHONUNBUFFERED=1

WORKDIR /

CMD [ "waitress-serve", "--port=5000", "--call", "app:create_app"]