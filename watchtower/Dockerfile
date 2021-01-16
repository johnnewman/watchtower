FROM python:3.7.9-buster AS wt-build

WORKDIR /watchtower

# Speed up install time by using precompiled packages at piwheels.
COPY ./ancillary/pi/pip.conf /etc/
COPY ./watchtower/requirements.txt ./
RUN pip install -r requirements.txt



# Builds then installs pytest
FROM wt-build as wt-build-test

RUN pip install pytest



# Starts uWSGI
FROM wt-build AS wt-run

COPY ./watchtower ./watchtower

ARG WATCHTOWER_UID
ARG VIDEO_GID
USER $WATCHTOWER_UID:$VIDEO_GID

CMD [ "uwsgi", "--ini", "/watchtower/watchtower/uwsgi.ini" ]



# Runs unit/integration tests
FROM wt-build-test AS wt-test

COPY ./watchtower ./watchtower

ARG WATCHTOWER_UID
ARG VIDEO_GID
USER $WATCHTOWER_UID:$VIDEO_GID

CMD [ "pytest" ]
