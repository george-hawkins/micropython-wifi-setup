# The MIT License (MIT)
# Copyright 2019 Jean-Christophe Bos & HC2 (www.hc2.fr)

from .libs.url_utils import UrlUtils
from .http_response import HttpResponse
import json
import sys

# ============================================================================
# ===( HttpRequest )==========================================================
# ============================================================================


class HttpRequest:

    MAX_RECV_HEADER_LINES = 100

    # ------------------------------------------------------------------------

    def __init__(self, config, xasCli, process_request):
        self._timeout_sec = config.timeout_sec
        self._xasCli = xasCli
        self._process_request = process_request

        self._httpVer = ""
        self._method = ""
        self._path = ""
        self._headers = {}
        self._content = None
        self._response = HttpResponse(config, self)

        self._recvLine(self._onFirstLineRecv)

    # ------------------------------------------------------------------------

    def _recvLine(self, onRecv):
        self._xasCli.AsyncRecvLine(onLineRecv=onRecv, timeoutSec=self._timeout_sec)

    # ------------------------------------------------------------------------

    def _onFirstLineRecv(self, xasCli, line, arg):
        try:
            elements = line.strip().split()
            if len(elements) == 3:
                self._httpVer = elements[2].upper()
                self._method = elements[0].upper()
                elements = elements[1].split("?", 1)
                self._path = UrlUtils.UnquotePlus(elements[0])
                self._queryString = elements[1] if len(elements) > 1 else ""
                self._queryParams = {}
                if self._queryString:
                    elements = self._queryString.split("&")
                    for s in elements:
                        p = s.split("=", 1)
                        if len(p) > 0:
                            v = UrlUtils.Unquote(p[1]) if len(p) > 1 else ""
                            self._queryParams[UrlUtils.Unquote(p[0])] = v
                self._recvLine(self._onHeaderLineRecv)
            else:
                self._response.ReturnBadRequest()
        except Exception as e:
            sys.print_exception(e)
            self._response.ReturnBadRequest()

    # ------------------------------------------------------------------------

    def _onHeaderLineRecv(self, xasCli, line, arg):
        try:
            elements = line.strip().split(":", 1)
            if len(elements) == 2:
                if len(self._headers) < HttpRequest.MAX_RECV_HEADER_LINES:
                    self._headers[elements[0].strip().lower()] = elements[1].strip()
                    self._recvLine(self._onHeaderLineRecv)
                else:
                    self._response.ReturnEntityTooLarge()
            elif len(elements) == 1 and len(elements[0]) == 0:
                self._process_request(self)
            else:
                self._response.ReturnBadRequest()
        except Exception as e:
            sys.print_exception(e)
            self._response.ReturnBadRequest()

    # ------------------------------------------------------------------------

    def async_data_recv(self, size, on_content_recv):
        def _on_content_recv(xasCli, content, arg):
            self._content = content
            on_content_recv()
            self._content = None

        self._xasCli.AsyncRecvData(
            size=size, onDataRecv=_on_content_recv, timeoutSec=self._timeout_sec
        )

    # ------------------------------------------------------------------------

    def GetPostedURLEncodedForm(self):
        res = {}
        if self.ContentType.lower() == "application/x-www-form-urlencoded":
            try:
                elements = bytes(self._content).decode("UTF-8").split("&")
                for s in elements:
                    p = s.split("=", 1)
                    if len(p) > 0:
                        v = UrlUtils.UnquotePlus(p[1]) if len(p) > 1 else ""
                        res[UrlUtils.UnquotePlus(p[0])] = v
            except Exception as e:
                sys.print_exception(e)
        return res

    # ------------------------------------------------------------------------

    def GetPostedJSONObject(self):
        if self.ContentType.lower() == "application/json":
            try:
                s = bytes(self._content).decode("UTF-8")
                return json.loads(s)
            except Exception as e:
                sys.print_exception(e)
        return None

    # ------------------------------------------------------------------------

    def GetHeader(self, name):
        if not isinstance(name, str) or len(name) == 0:
            raise ValueError('"name" must be a not empty string.')
        return self._headers.get(name.lower(), "")

    # ------------------------------------------------------------------------

    @property
    def UserAddress(self):
        return self._xasCli.CliAddr

    # ------------------------------------------------------------------------

    @property
    def HttpVer(self):
        return self._httpVer

    # ------------------------------------------------------------------------

    @property
    def Method(self):
        return self._method

    # ------------------------------------------------------------------------

    @property
    def Path(self):
        return self._path

    # ------------------------------------------------------------------------

    @property
    def QueryString(self):
        return self._queryString

    # ------------------------------------------------------------------------

    @property
    def QueryParams(self):
        return self._queryParams

    # ------------------------------------------------------------------------

    @property
    def Host(self):
        return self._headers.get("host", "")

    # ------------------------------------------------------------------------

    @property
    def Accept(self):
        s = self._headers.get("accept", None)
        if s:
            return [x.strip() for x in s.split(",")]
        return []

    # ------------------------------------------------------------------------

    @property
    def AcceptEncodings(self):
        s = self._headers.get("accept-encoding", None)
        if s:
            return [x.strip() for x in s.split(",")]
        return []

    # ------------------------------------------------------------------------

    @property
    def AcceptLanguages(self):
        s = self._headers.get("accept-language", None)
        if s:
            return [x.strip() for x in s.split(",")]
        return []

    # ------------------------------------------------------------------------

    @property
    def Cookies(self):
        s = self._headers.get("cookie", None)
        if s:
            return [x.strip() for x in s.split(";")]
        return []

    # ------------------------------------------------------------------------

    @property
    def CacheControl(self):
        return self._headers.get("cache-control", "")

    # ------------------------------------------------------------------------

    @property
    def Referer(self):
        return self._headers.get("referer", "")

    # ------------------------------------------------------------------------

    @property
    def ContentType(self):
        return self._headers.get("content-type", "").split(";", 1)[0].strip()

    # ------------------------------------------------------------------------

    @property
    def ContentLength(self):
        try:
            return int(self._headers.get("content-length", 0))
        except:
            return 0

    # ------------------------------------------------------------------------

    @property
    def UserAgent(self):
        return self._headers.get("user-agent", "")

    # ------------------------------------------------------------------------

    @property
    def Origin(self):
        return self._headers.get("origin", "")

    # ------------------------------------------------------------------------

    @property
    def IsUpgrade(self):
        return "upgrade" in self._headers.get("connection", "").lower()

    # ------------------------------------------------------------------------

    @property
    def Upgrade(self):
        return self._headers.get("upgrade", "")

    # ------------------------------------------------------------------------

    @property
    def Content(self):
        return self._content

    # ------------------------------------------------------------------------

    @property
    def Response(self):
        return self._response

    # ------------------------------------------------------------------------

    @property
    def XAsyncTCPClient(self):
        return self._xasCli


# ============================================================================
# ============================================================================
# ============================================================================
