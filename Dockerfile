FROM ubuntu:zesty

RUN apt-get update && apt-get install -y python-minimal python-pip
ADD *.py db requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt

EXPOSE 8000/tcp
WORKDIR /opt/app
CMD gunicorn -b 0.0.0.0:8000 --chdir /opt/app -w 1 --statsd-host statsd:8125 app
ENV COUCHDB_SERVER=couchdb
