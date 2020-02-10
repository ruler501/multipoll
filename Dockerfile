FROM python:3.7

RUN mkdir -p /multipoll
WORKDIR /multipoll
COPY ./requirements*.txt ./
RUN pip install -r requirements.txt --no-cache-dir

COPY ./ ./
