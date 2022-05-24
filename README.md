<h1 align="center">Execution bank bot</h1>

## Description

Телеграмм бот для удобного доступа к корпоративному банку.

## Запуск в docker

На основе <a  href="https://hub.docker.com/r/nektoman/sapnwsdk">готового контейнера</a>
```
docker build . -t bankbot:latest
docker run --name bankbot_prod --rm -d bankbot:latest config/[your_config_file]
```

## Запуск без docker

Для соединения с SAP NW через RFC используется <a  href="http://sap.github.io/PyRFC/install.html">PyRFC</a>, необходимо настроить окружение.

После этого:
```
pip install -r requirements.txt
python3 main.py config/[your_config_file]
