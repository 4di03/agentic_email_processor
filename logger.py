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



def logged_class(cls):
    """
    class decorator that logs all method calls and their arguments/results/exceptions
    """
    if not DEBUG:
        return cls# no-op if debugging is disabled

    log = Logger(context = "Logging Middleware for " + cls.__name__, debug=True)
    for name, attr in list(cls.__dict__.items()):
        if inspect.isfunction(attr):  # normal instance method
            @functools.wraps(attr)
            def wrapped(self, *args, __f=attr, __n=name, **kwargs):
                t0 = time.time()
                log.log("CALL %s.%s args=%r kwargs=%r", cls.__name__, __n, args, kwargs)
                try:
                    res = __f(self, *args, **kwargs)
                    log.log("RET  %s.%s -> %r (%.3fs)", cls.__name__, __n, res, time.time()-t0)
                    return res
                except Exception:
                    log.log("ERR  %s.%s", cls.__name__, __n)
                    raise
            setattr(cls, name, wrapped)
    return cls