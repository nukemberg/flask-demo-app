from functools import wraps
import time
import logging
import statsd


def TimerDecorator(metric_reporters, name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            res = func(*args, **kwargs)
            delta = time.time() - start
            for metric_reporter in metric_reporters:
                try:
                    metric_reporter(name, delta)
                except Exception:
                    logging.error("error while sending to %s", metric_reporter.__name__, exc_info=True)
            return res
        return wrapper
    return decorator


def statsd_client(addr):
    host, s_port = addr.split(":")
    port = int(s_port)
    return statsd.StatsClient(host, port, prefix='insult')
