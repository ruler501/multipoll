FROM python:3.7

RUN mkdir -p /multipoll
RUN mkdir -p /multipoll/multipoll
WORKDIR /multipoll
COPY ./requirements.txt /multipoll/requirements.txt
COPY ./manage.py /multipoll/manage.py
ADD ./multipoll /multipoll/multipoll/
RUN pip install -r requirements.txt
