FROM python:3

WORKDIR /usr/src/app

COPY . /usr/src/app

RUN pip install -r requirements.txt