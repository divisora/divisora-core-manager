## Divisora: Private, Automatic and Dynamic portal to other security zones
### Description
T.B.D

### Build / Run
#### Manually
```
podman build -t divisora/core-manager .
podman network create --subnet 192.168.66.0/24 --gateway 192.168.66.1 divisora_front
podman run --name divisora_core-manager --network divisora_front  --network-alias=core-manager -d divisora/core-manager:latest
```

#### Docker-Compose
```
cd docker
docker-compose build
docker-compose up --no-start
docker-compose start
```

### Default values
```
(Will be replaced with random and a OTP system later on)
user1 / test  Image: openbox-latest
user2 / test  Image: openbox-1.0
```

### Develope
#### Windows
```
python -m venv env
.\env\Scripts\activate

## Install
python -m pip install -r requirements.txt

## Run
$env:SECRET_KEY = "your secret key"
$env:DATABASE_URI = "postgresql://username:password@host:port/database_name"
$env:FLASK_APP = "app"
flask run --debug

## Create Requirements.txt
python -m pip install pip-tools
pip-compile --resolver=backtracking pyproject.toml
```
#### Linux
```
sudo apt-get install python3 python3-venv

python3 -m venv env
source env/bin/activate

## Install
python3 -m pip install -r requirements.txt
python3 -m pip install pip-tools

## Run
export SECRET_KEY="your secret key"
export DATABASE_URI="postgresql://username:password@host:port/database_name"
export FLASK_APP=app
flask run --debug

## Create Requirements.txt
#pip3 freeze > requirements.txt
pip-compile --resolver=backtracking pyproject.toml
```
