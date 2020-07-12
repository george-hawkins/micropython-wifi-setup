import sys

import logging

from slim.slim_server import SlimServer


_logger = logging.getLogger("route_module")


# MicroPython 1.12 doesn't have the enum module introduced in Python 3.4.
class HttpMethod:
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class RegisteredRoute:
    def __init__(self, method, routePath, handler):
        self._check_value("method", method, isinstance(method, str) and len(method) > 0)
        self._check_value(
            "routePath",
            routePath,
            isinstance(routePath, str) and routePath.startswith("/"),
        )
        method = method.upper()
        if len(routePath) > 1 and routePath.endswith("/"):
            routePath = routePath[:-1]

        self.Handler = handler
        self.Method = method
        self.RoutePath = routePath

    def _check_value(self, name, value, condition):
        if not condition:
            raise ValueError('{} is not a valid value for "{}"'.format(value, name))


class WebRouteModule:
    _MAX_CONTENT_LEN = 16 * 1024  # Content len from MicroWebSrv2.SetEmbeddedConfig

    def __init__(self, routes, max_content_len=_MAX_CONTENT_LEN):
        self._max_content_len = max_content_len
        self._registeredRoutes = routes

    def OnRequest(self, request):
        route_result = self._resolve_route(request.Method, request.Path)
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
                    _logger.error(
                        "not enough memory to read a content of %s bytes.", cnt_len
                    )
                    request.Response.ReturnServiceUnavailable()
            else:
                request.Response.ReturnEntityTooLarge()
        else:
            request.Response.ReturnBadRequest()

    def _route_request(self, request, route_result):
        try:
            route_result.Handler(request)
            if not request.Response.HeadersSent:
                _logger.warning("no response was sent from route %s.", route_result)
                request.Response.ReturnNotImplemented()
        except Exception as ex:
            sys.print_exception(ex)
            _logger.error("exception raised from route %s", route_result)
            request.Response.ReturnInternalServerError()

    def _resolve_route(self, method, path):
        path = path.lower()
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        for regRoute in self._registeredRoutes:
            if regRoute.Method == method and regRoute.RoutePath == path:
                return regRoute
        return None
