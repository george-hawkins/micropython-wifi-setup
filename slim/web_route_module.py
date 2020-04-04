from slim.MicroWebSrv2.webRoute import ResolveRoute
from slim.slim_server import SlimServer


class WebRouteModule:
    _MAX_CONTENT_LEN = 16 * 1024  # Content len from MicroWebSrv2.SetEmbeddedConfig

    def __init__(self, logger, max_content_len=_MAX_CONTENT_LEN):
        self._logger = logger
        self._max_content_len = max_content_len

    def OnRequest(self, request):
        if request.IsUpgrade:
            return

        route_result = ResolveRoute(request.Method, request.Path)
        if not route_result:
            return

        def route_request():
            self._route_request(request, route_result)

        cnt_len = request.ContentLength
        if not cnt_len:
            route_request()
        elif request.Method not in ("GET", "HEAD"):
            if cnt_len <= self._max_content_len:
                try:
                    request.async_data_recv(size=cnt_len, on_content_recv=route_request)
                    return SlimServer.RESPONSE_PENDING
                except:
                    self._logger.error(
                        "Not enough memory to read a content of %s bytes." % cnt_len
                    )
                    request.Response.ReturnServiceUnavailable()
            else:
                request.Response.ReturnEntityTooLarge()
        else:
            request.Response.ReturnBadRequest()

    def _route_request(self, request, route_result):
        try:
            if route_result.Args:
                route_result.Handler(request, route_result.Args)
            else:
                route_result.Handler(request)
            if not request.Response.HeadersSent:
                self._logger.warning("No response was sent from route %s." % route_result)
                request.Response.ReturnNotImplemented()
        except Exception as ex:
            self._logger.error("Exception raised from route %s: %s" % (route_result, ex))
            request.Response.ReturnInternalServerError()