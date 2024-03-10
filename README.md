## Divisora: Private, Automatic and Dynamic portal to other security zones
## Description
T.B.D

## Build / Run
### Manually
```
podman build -t divisora/core-manager .
podman network create --subnet 192.168.66.0/24 --gateway 192.168.66.1 divisora_front
podman run --name divisora_core-manager --network divisora_front  --network-alias=core-manager -d divisora/core-manager:latest
```

### Docker-Compose
#### Main
```
docker-compose build
docker-compose up --no-start
docker-compose start
```
#### Locally (debug)
```
docker-compose -f .\docker-compose.local.yml up --detach --build --force-recreate
```

## Default values
```
Portal Login:
(Will be replaced with random and a OTP system later on)

username    password    image
admin       admin       openbox-latest
user1       test        openbox-latest
user2       test        openbox-1.0

system      random()    none
anonymous   random()    none
```

## Develope
### Windows
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
### Linux
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

# Ubuntu 22.04
```
apt-get update && apt-get upgrade -y
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update

for pkg in docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose docker-compose-plugin; do sudo apt-get install $pkg; done

cd examples
docker-compose docker-compose.yml build web
docker-compose up -d

# Rebuild / Restart
docker-compose up --detach --build --force-recreate
```