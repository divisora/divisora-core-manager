FROM docker.io/library/python:3.10-alpine

WORKDIR /app

COPY requirements.txt /app/
#RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY app /app/

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP="app"

WORKDIR /

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0" ]