FROM python:3.7

RUN mkdir -p /multipoll
RUN mkdir -p /multipoll/multipoll
WORKDIR /multipoll
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY ./manage.py ./manage.py
COPY ./multipoll ./multipoll/
