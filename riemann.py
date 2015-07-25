import socket
from bernhard import Client


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

    def riemann_timer_reporter(self, service, metric):
        self.send(dict(service=service, metric=metric, tags=['timer']))


def get_client(riemann_addr, **kwargs):
    riemann_host, riemann_port = riemann_addr.split(":")
    return TaggedClient(host=riemann_host, port=int(riemann_port), **kwargs)


def wsgi_middelware(next_middleware, riemann_client, host=socket.gethostname()):
    def call(environ, start_response):
        try:
            iterable = next_middleware(environ, start_response)
            for data in iterable:
                yield data
        except Exception as e:
            riemann_client.send({"service": "exception", "description": str(e), "metric": 1, "tags": ["counter"]})
            raise
    return call
