FROM python:3

WORKDIR /watchtower

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

# Move the configs into the instance folder.
COPY ./watchtower/config/*.json ./instance/

ARG SERVER_UID
ARG SERVER_GID

USER $SERVER_UID:$SERVER_GID

CMD [ "uwsgi", "--ini", "/watchtower/uwsgi.ini" ]
