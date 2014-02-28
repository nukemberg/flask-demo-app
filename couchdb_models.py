from flaskext.couchdb import *
from flask.ext.restful import fields
from flask_restful_swagger import swagger

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

def update_design_doc(ddoc):
	ddoc['updates'] = {"increment_score": update_score_func}