import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
COUCHDB_SERVER = "http://{}:5984".format(os.getenv("COUCHDB_SERVER", "localhost"))
