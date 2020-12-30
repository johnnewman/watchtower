FROM python:3.7.9-buster

# Install all dependencies for opencv-python-headless
RUN apt-get update && apt-get install -y \
  libaom0 \
  libatlas3-base \
  libavcodec58 \
  libavformat58 \
  libavutil56 \
  libbluray2 \
  libcairo2 \
  libchromaprint1 \
  libcodec2-0.8.1 \
  libcroco3 \
  libdatrie1 \
  libdrm2 \
  libfontconfig1 \
  libgdk-pixbuf2.0-0 \
  libgfortran5 \
  libgme0 \
  libgraphite2-3 \
  libgsm1 \
  libharfbuzz0b \
  libilmbase23 \
  libjbig0 \
  libmp3lame0 \
  libmpg123-0 \
  libogg0 \
  libopenexr23 \
  libopenjp2-7 \
  libopenmpt0 \
  libopus0 \
  libpango-1.0-0 \
  libpangocairo-1.0-0 \
  libpangoft2-1.0-0 \
  libpixman-1-0 \
  librsvg2-2 \
  libshine3 \
  libsnappy1v5 \
  libsoxr0 \
  libspeex1 \
  libssh-gcrypt-4 \
  libswresample3 \
  libswscale5 \
  libthai0 \
  libtheora0 \
  libtiff5 \
  libtwolame0 \
  libva-drm2 \
  libva-x11-2 \
  libva2 \
  libvdpau1 \
  libvorbis0a \
  libvorbisenc2 \
  libvorbisfile3 \
  libvpx5 \
  libwavpack1 \
  libwebp6 \
  libwebpmux3 \
  libx264-155 \
  libx265-165 \
  libxcb-render0 \
  libxcb-shm0 \
  libxfixes3 \
  libxrender1 \
  libxvidcore4 \
  libzvbi0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /watchtower

# Speed up install time by using precompiled packages at piwheels.
COPY ./ancillary/pip.conf /etc/
COPY ./watchtower/requirements.txt ./
RUN pip install -r requirements.txt

COPY ./watchtower ./watchtower
COPY ./config ./config

ARG WATCHTOWER_UID
ARG VIDEO_GID

USER $WATCHTOWER_UID:$VIDEO_GID

CMD [ "uwsgi", "--ini", "/watchtower/watchtower/uwsgi.ini" ]
