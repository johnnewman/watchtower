FROM python:3.7.9-buster

WORKDIR /microcontroller

# Speed up install time by using precompiled packages at piwheels.
COPY pip.conf /etc/
COPY ./microcontroller/requirements.txt ./
RUN pip install -r requirements.txt

COPY ./microcontroller .

CMD [ "python3", "-u", "server.py" ]
