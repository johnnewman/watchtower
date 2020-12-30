FROM python:3.7.9-buster

WORKDIR /microcontroller

# Speed up install time by using precompiled packages at piwheels.
COPY ./ancillary/pi/pip.conf /etc/
COPY ./microcontroller/requirements.txt ./
RUN pip install -r requirements.txt

COPY ./microcontroller .

ARG WATCHTOWER_UID
ARG SERIAL_GID

USER $WATCHTOWER_UID:$SERIAL_GID

CMD [ "python3", "-u", "server.py" ]
