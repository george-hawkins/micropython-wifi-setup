from slim.logger import Logger


class SlimConfig:
    _DEFAULT_TIMEOUT = 2  # 2 seconds (originally from MicroWebSrv2.__init__).

    def __init__(
        self,
        logger=Logger(),
        timeout_sec=_DEFAULT_TIMEOUT,
        allow_all_origins=False,
        not_found_url=None,
    ):
        self.logger = logger
        self.timeout_sec = timeout_sec
        self.allow_all_origins = allow_all_origins
        self.not_found_url = not_found_url
