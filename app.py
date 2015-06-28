#!/usr/bin/env python

from flask import Flask, render_template, abort, g, request, json, redirect, appcontext_pushed
from flask.ext import restful
from flask.ext.restful import fields, marshal_with, marshal
from flask_restful_swagger import swagger
import riemann
import couchdb
from flaskext.couchdb import CouchDBManager, paginate
from couchdb_models import Insult, category_scores, update_design_doc
from functools import wraps
import random

__version__ = "0.0.1"

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(
    COUCHDB_DATABASE="insults",
    COUCHDB_SERVER="http://localhost:5984",
    RIEMANN_ADDRESS="localhost:5555",
    BASE_URL="http://localhost:5000"
    ))
app.config.from_envvar('APP_CONFIG_FILE', silent=True)

api = swagger.docs(restful.Api(app), apiVersion="1.0.0", basePath=app.config['BASE_URL'])

# couchdb setup
couchdb_manager = CouchDBManager(auto_sync=False)
couchdb_manager.setup(app)
couchdb_manager.add_document(Insult)
couchdb_manager.add_viewdef(category_scores)
# install a hook so we have a chance to put update function into the design document
couchdb_manager.update_design_doc = update_design_doc
couchdb_manager.sync(app)

riemann_client = riemann.get_client(app.config['RIEMANN_ADDRESS'], tags=[__version__])

app.wsgi_app = riemann.WSGIMiddleware(app.wsgi_app, riemann_client)

# get a timer decorator with riemann client pre-injected
timed = riemann.TimerDecorator(riemann_client)

@appcontext_pushed.connect_via(app)
def _connect_riemann(_app, **kwargs):
    try:
        if not riemann_client.connection:
            riemann_client.connect()
    except Exception:
        _app.warning("Failed to connect to riemann", exc_info=True)


# field spec for id only answer
@swagger.model
class IdOnlyModel(object):
    resource_fields = {
        "id": fields.String
    }


def retry(catch, attempts, on_failure):
    "A decorator that will retry an operation `attempts` times and will call `on_failure` if retries exhausted"
    def decorator(func):
        @wraps
        def wrapper_func(*args, **kwargs):
            for _ in xrange(attempts):
                try:
                    return func(*args, **kwargs)
                except catch:
                    pass
            else:
                on_failure()
        return wrapper_func
    return decorator


class InsultController(restful.Resource):
    @swagger.operation(notes="Retrieve a specific insult by ID", responseClass=Insult.__name__)
    @marshal_with(Insult.resource_fields)
    def get(self, insult_id):
        doc = Insult.load(insult_id)
        if doc is None: abort(404)
        return doc

    @swagger.operation(
        notes="Update a specific insult by ID",
        responseClass=Insult.__name__,
        parameters=[
            {"name": "body", "description": "Updated insult document", "paramType": "body", "required": True, "dataType": Insult.__name__}
        ])
    @marshal_with(Insult.resource_fields)
    def put(self, insult_id):
        def _failed():
            restful.abort(409, {"status": "document conflict", "id": insult_id})

        #Updates the insult with a retry. Will attempt 3 times before failing.
        @retry(catch=couchdb.http.ResourceConflict, attempts=3, on_failure=_failed)
        def _update_doc(doc):
            doc.update(request.get_json())
            g.couch.save(doc)
            return doc

        doc = Insult.load(insult_id)
        if doc is None:
            restful.abort(404, status="Not found")

        return _update_doc(doc)

    def delete(self, insult_id):
        try:
            del g.couch[insult_id]
            return True
        except couchdb.http.ResourceNotFound:
            restful.abort(404, status="Not found")


class InsultCategoryController(restful.Resource):
    "Returns all the insults in the category with the given ID"
    @timed("list category items")
    def get(self, category):
        try:
            pagination = paginate(Insult.by_category(key=category, include_docs=True, reduce=False), 50, request.args.get('start', None))
        except TypeError:
            app.logger.error("Error while paginating category items", exc_info=True)
            abort(400)
        return {"next": json.loads(pagination.next), "insults": marshal([row.doc for row in pagination.items], Insult.resource_fields)}


class InsultsController(restful.Resource):
    @swagger.operation(
        notes="Submit a new insult",
        responseClass=IdOnlyModel.__name__,
        parameters=[
            {"name": "body", "paramType": "body", "dataType": Insult.__name__, "required": True}
        ])
    @timed("new insult")
    @marshal_with(IdOnlyModel.resource_fields)
    def post(self):
        doc = Insult(**request.get_json())
        doc.store()
        return doc

    @timed("list insults")
    def get(self):
        try:
            page = paginate(Insult.score_view(include_docs=True), 50, request.args.get('start', None))
        except TypeError:
            app.logger.error("Error while paginating insults", exc_info=True)
            abort(400)
        return {"next": json.loads(page.next), "insults": marshal([row.doc for row in page.items], Insult.resource_fields)}


class CategoriesController(restful.Resource):
    "Lists all the categories by their like score."
    def get(self):
        d = {row.key: row.value for row in category_scores(group=True)}
        return sorted(d, key=d.get) # return sorted list by score


class InsultLikeController(restful.Resource):
    "increment the score of a insult with a given ID"
    def put(self, insult_id):
        riemann_client.send({"service": "like", "metric": 1, "tags": ["counter"]})
        _, resp_body = g.couch.update_doc("insults/increment_score", insult_id)
        # resp_body is a StringIO object
        return json.load(resp_body)


class InsultRandomController(restful.Resource):
    @swagger.operation(
        notes="Get a random insult",
        responseClass=Insult.__name__,
    )
    @timed("random insult")
    @marshal_with(Insult.resource_fields)
    def get(self):
        # This random selection method is flawed. It's biased and doesn't give the same chance to all documents
        # On top of that, the CoudchDB view generation is bad since it uses random in the map
        rand_id = random.random()
        docs = Insult.by_random_id(startkey=rand_id, limit=1, include_docs=True)
        if len(docs) == 0:
            docs = Insult.by_ordered_id(startkey=rand_id, limit=1, descending=True, include_docs=True)
        return docs.rows[0].doc

api.add_resource(InsultRandomController, "/insult/_random")
api.add_resource(InsultController, "/insult/<string:insult_id>")
api.add_resource(InsultsController, "/insult", "/insult/")
api.add_resource(InsultCategoryController, "/category/<string:category>")
api.add_resource(CategoriesController, "/category", "/category/")
api.add_resource(InsultLikeController, "/insult/<string:insult_id>/like")


@app.route("/")
def index():
    return redirect("/api/spec.html")


if __name__ == '__main__':
    app.run(debug=True)
