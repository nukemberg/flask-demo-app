from functools import wraps
import time
import socket
from bernhard import Client
import logging

class TaggedClient(Client):
	def __init__(self, *args, **kwargs):
		self._local_hostname = kwargs.pop('local_hostname', socket.gethostname())
		self._tags = kwargs.pop('tags', [])
		self._service_prefix = kwargs.pop('service_prefix', 'InsultsAPI')
		super(TaggedClient, self).__init__(*args, **kwargs)

	def send(self, event):
		event['host'] = self._local_hostname
		event['tags'] = event.get('tags', []) + self._tags
		event['service'] = self._service_prefix + " " + event['service']
		return super(TaggedClient, self).send(event)

def get_client(riemann_addr, **kwargs):
	riemann_host, riemann_port = riemann_addr.split(":")
	return TaggedClient(host=riemann_host, port=int(riemann_port), **kwargs)

class TimerDecorator(object):
	def __init__(self, riemann_client):
		self._riemann_client = riemann_client

	def __call__(self, name):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				start = time.time()
				res = func(*args, **kwargs)
				try:
					self._riemann_client.send({"service": name, "metric": time.time() - start, "tags":["timer"]})
				except Exception as e:
					logging.error("error while sending to riemann", exc_info=True)
				return res
			return wrapper
		return decorator

class WSGIMiddleware(object):
	def __init__(self, next_middleware, riemann_client, host=socket.gethostname()):
		self._riemann_client = riemann_client
		self._host = host
		self._next_middleware = next_middleware

	def __call__(self, environ, start_response):
		try:
			iterable = self._next_middleware(environ, start_response)
			for data in iterable: yield data
		except Exception as e:
			self._riemann_client.send({"service": "exception", "description": str(e), "metric": 1, "tags": ["counter"]})
			raise

