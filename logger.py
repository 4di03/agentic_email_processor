DEFAULT_LOG_FILE = "logs/debug.log"
import functools, inspect, logging, time
from constants import DEBUG
class Logger:

    def __init__(self, log_file: str | None = DEFAULT_LOG_FILE, debug = False, context = None):
        self.log_file = log_file
        self.debug = debug
        self.context = context

    def _log(self, message: str):
        if self.context:
            message = f"[{self.context}] {message}"
        # if self.debug:
        #     print(message)

        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')

    def log(self, fmt: str, *args):
        """
        Formatted log: log("CALL %s.%s args=%r", cls, name, args)
        """

        # if no args, log fmt directly
        if not args:
            return self._log(fmt)


        self.log(fmt % args)


import functools
import inspect
import time

def logged_class(cls):
    """ class decorator that logs all method calls and their arguments/results/exceptions """
    if not DEBUG:
        return cls

    log = Logger(context="Logging Middleware for " + cls.__name__, debug=True)

    def _log_call(name, args, kwargs):
        log.log("CALL %s.%s args=%r kwargs=%r", cls.__name__, name, args, kwargs)

    def _log_ret(name, res, dt):
        log.log("RET  %s.%s -> %r (%.3fs)", cls.__name__, name, res, dt)

    def _log_err(name):
        log.log("ERR  %s.%s", cls.__name__, name)

    for name, attr in list(cls.__dict__.items()):
        if not inspect.isfunction(attr):
            continue

        if inspect.iscoroutinefunction(attr):
            @functools.wraps(attr)
            async def wrapped(self, *args, __f=attr, __n=name, **kwargs):
                t0 = time.perf_counter()
                _log_call(__n, args, kwargs)
                try:
                    res = await __f(self, *args, **kwargs)
                    _log_ret(__n, res, time.perf_counter() - t0)
                    return res
                except Exception:
                    _log_err(__n)
                    raise
            setattr(cls, name, wrapped)
        else:
            @functools.wraps(attr)
            def wrapped(self, *args, __f=attr, __n=name, **kwargs):
                t0 = time.perf_counter()
                _log_call(__n, args, kwargs)
                try:
                    res = __f(self, *args, **kwargs)
                    _log_ret(__n, res, time.perf_counter() - t0)
                    return res
                except Exception:
                    _log_err(__n)
                    raise
            setattr(cls, name, wrapped)

    return cls
