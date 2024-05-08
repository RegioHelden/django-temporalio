FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

RUN useradd -m app

USER app
WORKDIR /app

ADD requirements-ci.txt /app/
ADD requirements-test.txt /app/

ENV PATH /home/app/venv/bin:$PATH

RUN python3 -m venv ~/venv && \
    pip install -r requirements-test.txt

ADD . /app/

ENV DJANGO_SETTINGS_MODULE dev.settings
