FROM debian:bookworm-slim

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8
ARG DEBIAN_FRONTEND=noninteractive

USER root

RUN apt-get -y update && apt-get -y --no-install-recommends install \
    build-essential \
    gcc \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    gettext \
    && \
    rm -rf /var/lib/apt/lists/* /usr/share/doc/* /usr/share/locale/* /usr/share/man/* && \
    mkdir -p /app && \
    (useradd -m app || true)

WORKDIR /app

USER app

ADD requirements-test.txt /app/

ENV PATH /home/app/venv/bin:$PATH
ENV PKG_PIP_VERSION=24.0

RUN python3 -m venv ~/venv && \
    pip install pip==${PKG_PIP_VERSION} && \
    pip install wheel && \
    pip install -r requirements-test.txt

ADD . /app/

ENV DJANGO_SETTINGS_MODULE dev.settings
