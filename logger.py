DEFAULT_LOG_FILE = "logs/debug.log"

class Logger:

    def __init__(self, log_file: str | None = DEFAULT_LOG_FILE, debug = False, context = None):
        self.log_file = log_file
        self.debug = debug
        self.context = context

    def log(self, message: str):
        if self.context:
            message = f"[{self.context}] {message}"
        if self.debug:
            print(message)

        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')