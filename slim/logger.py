class Logger:
    def debug(self, msg):
        self._log("DEBUG", msg)

    def info(self, msg):
        self._log("INFO", msg)

    def warning(self, msg):
        self._log("WARNING", msg)

    def error(self, msg):
        self._log("ERROR", msg)

    def _log(self, msg_type, msg):
        print("MWS2-{}> {}".format(msg_type, msg))


logger = Logger()
