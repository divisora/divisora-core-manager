FROM python:3.10

# Dependencies for matplotlib(Numpy)
#RUN apk --no-cache add musl-dev linux-headers g++ make

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py .
COPY app ./app

ENV PYTHONUNBUFFERED=1

CMD [ "waitress-serve", "--port=5000", "--call", "app:create_app"]