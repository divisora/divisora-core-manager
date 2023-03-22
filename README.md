## Divisora: Private, Automatic and Dynamic portal to other security zones
### Description
T.B.D

### Build / Run
```
podman build -t divisora/core-manager .
podman network create --subnet 192.168.66.0/24 --gateway 192.168.66.1 divisora_front
podman run --name divisora_core-manager --network divisora_front  --network-alias=core-manager -d divisora/core-manager:latest
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
$env:FLASK_APP = "run.py"
flask run

## Create Requirements.txt
#pip3 freeze > requirements.txt
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
flask run

## Create Requirements.txt
#pip3 freeze > requirements.txt
pip-compile --resolver=backtracking pyproject.toml
```

#### Redis (not used yet)
```
celery -A run worker --loglevel INFO

## Test redis
podman run --name redis -p 6379:6379 -d docker.io/library/redis:latest
celery -A run worker --loglevel INFO
FLASK_APP=run.py flask shell
from app.auth.tasks import divide
task = divide.delay(1, 2)

### Output
[2023-03-18 12:28:32,359: INFO/MainProcess] Connected to redis://localhost:6379//
[2023-03-18 12:28:32,361: INFO/MainProcess] mingle: searching for neighbors
[2023-03-18 12:28:33,411: INFO/MainProcess] mingle: all alone
[2023-03-18 12:28:33,417: INFO/MainProcess] celery@node2.domain.internal ready.
[2023-03-18 12:30:42,182: INFO/MainProcess] Task app.auth.tasks.divide[d1decda8-a4df-412b-ae6e-f5e908d91fa2] received
[2023-03-18 12:30:47,212: INFO/ForkPoolWorker-2] Task app.auth.tasks.divide[d1decda8-a4df-412b-ae6e-f5e908d91fa2] succeeded in 5.0296678860001975s: 0.5
```
