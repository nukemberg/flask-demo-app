# Playground application for Riemann workshop

This is a [Flask](http://flask.pocoo.org/docs/) based playground application for a Riemann workshop. The point is to have some application we can experiment on to generate metrics and events for Riemann.

The behaviour of this application can be pretty bad, which is very good for the workshop... don't take it as an example of a well-written application.

## Requirements

For python requirements, see the `requirements.txt` file or just use `pip install -r requirements.txt`

Other then that the application depends on [CouchDB](http://couchdb.apache.org/) and [Riemann](http://riemann.io/).

## Configuration

To specify a config file, set the `APP_CONFIG_FILE` environment variable to name of a python config file. Here is a list of configuration variables and their defaults:

- COUCHDB_DATABASE="insults",
- COUCHDB_SERVER="http://localhost:5984",
- RIEMANN_ADDRESS="localhost:5555"
- BASE_URL="http://localhost:5000" - base url for swagger. For use with WSGI servers or proxies

## How to run

To start the development server simply run app.py:

    python app.py

To run with a production grade WSGI server (e.g. gunicorn):

    gunicorn -w 2 -e APP_CONFIG_FILE=config.py -b :8080 app:app

## Populating the database

In the `db` folder there is a list file containing insult documents. To populate the database use the import tools:

    python db/import.py -u http://localhost:5984/insults db/insults.list

## Credits, Projects used

This application uses the following Open Source libraries

- [Flask](http://flask.pocoo.org/docs/)
- [flask-restful](http://flask-restful.readthedocs.org/en/latest/)
- [flask-restful-swagger](https://github.com/rantav/flask-restful-swagger) (by Ran Tavory)
- [flask-couchdb](https://pythonhosted.org/Flask-CouchDB)
- [python-couchdb](https://pythonhosted.org/CouchDB/)
- [Bernhard](https://github.com/banjiewen/bernhard) Riemann client