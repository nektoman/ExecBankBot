FROM nektoman/sapnwsdk:latest
#ENV
COPY requirements.txt /bankbot_app/
RUN apt update && apt install python3-pip -y && pip install -r /bankbot_app/requirements.txt && apt remove python3-pip -y && apt autoremove -y && apt clean && rm -rf /var/cache/apt
#CODE
COPY ./bankbot_app /bankbot_app/
WORKDIR /bankbot_app
#START
ENTRYPOINT [ "python3", "main.py" ]
CMD ["config/sapnwrfc_test.cfg"]
#docker build . -t bankbot:latest
#docker run --name bankbot_prod --rm -d bankbot:latest config/sapnwrfc_prod.cfg