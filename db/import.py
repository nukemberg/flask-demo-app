#! /usr/bin/env python

import json
import requests
from argparse import ArgumentParser
import urlparse, sys

def chunks(iterator, n):
    return (iterator[pos:pos + n] for pos in xrange(0, len(iterator), n))
parser = ArgumentParser()
parser.add_argument("-u", help="couchdb url", dest="url", type=str, required=True)
parser.add_argument("insults_file", help="insults file (json formatted lines)")

opts = parser.parse_args()
url = urlparse.urljoin(opts.url.rstrip("/") + "/", "_bulk_docs")

resp = requests.get(opts.url, headers={"Content-Type": "application/json"})
if not resp.ok:
    print "Creating database"
    requests.put(opts.url, headers={"Content-Type": "application/json"})

with open(opts.insults_file) as f:
    for chunk in chunks(f.readlines(), 100):
        data = {"docs": [json.loads(r) for r in chunk]}
        resp = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        if not resp.ok:
            print >> sys.stderr, "Update failed, code: %d, %s" % (resp.status_code, resp.text)
            sys.exit(1)
