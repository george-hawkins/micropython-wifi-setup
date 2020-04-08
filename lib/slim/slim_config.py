class SlimConfig:
    _DEFAULT_TIMEOUT = 4  # 4 seconds - 2 seconds is too low for some mobile browsers.

    def __init__(
        self,
        timeout_sec=_DEFAULT_TIMEOUT,
        allow_all_origins=False,
        not_found_url=None,
        server_name="Slim Server (MicroPython)",
    ):
        self.timeout_sec = timeout_sec
        self.allow_all_origins = allow_all_origins
        self.not_found_url = not_found_url
        self.server_name = server_name
