# This is a tweaked Dockerfile from the official Motion Project Dockerfile
# here: https://hub.docker.com/r/motionproject/motion/dockerfile
#
# Use a MOTION_RELEASE_TAG environment variable to specify the exact git tag
# of Motion Project that you'd like to build, like "release-4.3.2".

FROM debian:buster AS build

# Install dependencies
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    autopoint \
    pkgconf \
    libtool \
    libjpeg62-turbo-dev \
    build-essential \
    libzip-dev \
    gettext \
    libmicrohttpd-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    ca-certificates \
    git && \
    apt-get -y autoremove && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

ARG MOTION_RELEASE_TAG

# Checkout and build motion
RUN git clone https://github.com/Motion-Project/motion.git  && \
    cd motion  && \
    git checkout $MOTION_RELEASE_TAG && \
    autoreconf -fiv && \
    ./configure && \
    make clean && \
    make && \
    make install && \
    cd .. && \
    rm -rf motion


FROM debian:buster

# Copy the compiled Motion program
COPY --from=build /usr/local /usr/local

# Install runtime dependencies used by ffmpeg and install curl.
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    curl \
    libjpeg62 \
    libmicrohttpd12 \
    libavutil56 \
    libavformat58 \
    libavdevice58 \
    libswscale5 && \
    apt-get -y autoremove && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

VOLUME /usr/local/etc/motion

CMD [ "motion", "-n" ]
