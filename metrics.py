from functools import wraps
import time
import logging
import statsd


def _name(obj):
    return getattr(obj, '__name__', obj.__class__.__name__)


def TimerDecorator(metric_reporters, name):
    def decorator(func):
        def _report(m, value):
            for metric_reporter in metric_reporters:
                try:
                    if getattr(metric_reporter, '_units', 's') == 'ms':
                        value = value * 1000
                    metric_reporter(m, value)
                except Exception:
                    logging.error("error while sending to %s", _name(metric_reporter), exc_info=True)

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                res = func(*args, **kwargs)
            except Exception:
                _report(name + '.error', time.time() - start)
                raise
            _report(name + '.success', time.time() - start)

            return res
        return wrapper
    return decorator


def units(unit):
    def decorator(f):
        f._units = unit
        return f
    return decorator


class StatsClient(statsd.StatsClient):
    @units("ms")
    def timing(self, name, value):
        super(StatsClient, self).timing(name.replace(" ", "_"), value)

    def incr(self, stat, count=1, rate=1):
        super(StatsClient, self).incr(stat.replace("", "_"), count, rate)

    def decr(self, stat, count=1, rate=1):
        super(StatsClient, self).decr(stat.replace("", "_"), count, rate)


def statsd_client(addr):
    host, s_port = addr.split(":")
    port = int(s_port)
    return StatsClient(host, port, prefix='insult')


def statsd_wsgi_middelware(next_middleware, statsd_client):
    def call(environ, start_response):
        try:
            iterable = next_middleware(environ, start_response)
            for data in iterable:
                yield data
        except Exception:
            statsd_client.incr("exception")
            raise
    return call
