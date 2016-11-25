from flaskext.couchdb import *
from flask_restful import fields
from flask_restful_swagger import swagger


# field spec for id only answer
@swagger.model
class IdOnlyModel(object):
    resource_fields = {
        "id": fields.String
    }


@swagger.model
class Insult(Document):
    doc_type = 'insult'
    author = TextField()
    insult = TextField()
    category = TextField()
    score = IntegerField()

    resource_fields = {
        'id': fields.String,
        'category': fields.String,
        'author': fields.String,
        'insult': fields.String
    }

    def as_dict(self):
        return dict(self.items())

    by_category = ViewField('insults', """
function (doc) {
    if (doc.doc_type == 'insult') {
        emit(doc.category.toLowerCase(), null)
    }
}""", "_count", wrapper=Row)
    score_view = ViewField('insults', """
function (doc) {
    if (doc.doc_type == 'insult') {
        emit(doc.score, null)
    }
}
""", wrapper=Row)

    # Bad, bad boy...
    by_random_id = ViewField('insults', """
function (doc) {
    if (doc.doc_type == 'insult') {
        emit(Math.random(), null);
    }
}
""", wrapper=Row)

category_scores = ViewDefinition('insults', 'category_by_score', """
function (doc) {
    if (doc.doc_type == 'insult') {
        emit(doc.category, doc.score == null ? 0 : doc.score);
    }
}""",
    "_sum", wrapper=Row)

update_score_func = """
function (doc, request) {
    if (!doc) {
        return [null, {"body": toJSON({"status": "not found"}), "code": 404}];
    }
    if (doc['doc_type'] == 'insult') {
        doc['score'] += 1;
        return [doc, toJSON({"status": "updated"})];
    }
    return [null, {"body": toJSON({"status": "incorrect document type"}), "code": 412}];
}
"""

@swagger.model
class Insults(object):
    resource_fields = {
        "insults": fields.List(fields.Nested(Insult))
    }

@swagger.model
class LogEntry(Document):
    doc_type = 'logEntry'
    time = DateTimeField()
    path = TextField()
    method = TextField()
    document_id = TextField()
    ip = TextField()
    status = TextField()

log_entries = ViewDefinition('insults', 'log_entries', """
function(doc) {
    if (doc.doc_type == 'logEntry') {
        emit(doc.time, doc);
    }
}
""")


def update_design_doc(ddoc):
    ddoc['updates'] = {"increment_score": update_score_func}
