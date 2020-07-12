# The MIT License (MIT)
# Copyright 2019 Jean-Christophe Bos & HC2 (www.hc2.fr)

from os import stat
import json
import sys

import logging


_logger = logging.getLogger("response")


# Read a file, given a path relative to the directory containing this `.py` file.
def _read_relative(filename):
    from shim import join, dirname, read_text

    return read_text(join(dirname(__file__), filename))


# ============================================================================
# ===( HttpResponse )=========================================================
# ============================================================================


class HttpResponse:

    _RESPONSE_CODES = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Long",
        415: "Unsupported Media Type",
        416: "Requested Range Not Satisfiable",
        417: "Expectation Failed",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
    }

    _CODE_CONTENT_TMPL = _read_relative("status-code.html")

    # ------------------------------------------------------------------------

    def __init__(self, config, request):
        self._not_found_url = config.not_found_url
        self._allow_all_origins = config.allow_all_origins
        self._server_name = config.server_name

        self._request = request
        self._xasCli = request.XAsyncTCPClient

        self._headers = {}
        self._allowCaching = False
        self._acAllowOrigin = None
        self._contentType = None
        self._contentCharset = None
        self._contentLength = 0
        self._stream = None
        self._sendingBuf = None
        self._hdrSent = False

        self._switch_result = None

    # ------------------------------------------------------------------------

    def SetHeader(self, name, value):
        if not isinstance(name, str) or len(name) == 0:
            raise ValueError('"name" must be a not empty string.')
        if value is None:
            raise ValueError('"value" cannot be None.')
        self._headers[name] = str(value)

    # ------------------------------------------------------------------------

    def _onDataSent(self, xasCli, arg):
        if self._stream:
            try:
                n = self._stream.readinto(self._sendingBuf)
                if n < len(self._sendingBuf):
                    self._stream.close()
                    self._stream = None
                    self._sendingBuf = self._sendingBuf[:n]
            except Exception as e:
                sys.print_exception(e)
                self._xasCli.Close()
                _logger.error(
                    'stream cannot be read for request "%s".', self._request._path
                )
                return
        if self._sendingBuf:
            if self._contentLength:
                self._xasCli.AsyncSendSendingBuffer(
                    size=len(self._sendingBuf), onDataSent=self._onDataSent
                )
                if not self._stream:
                    self._sendingBuf = None
            else:

                def onChunkHdrSent(xasCli, arg):
                    def onChunkDataSent(xasCli, arg):
                        def onLastChunkSent(xasCli, arg):
                            self._xasCli.AsyncSendData(
                                b"0\r\n\r\n", onDataSent=self._onDataSent
                            )

                        if self._stream:
                            onDataSent = self._onDataSent
                        else:
                            self._sendingBuf = None
                            onDataSent = onLastChunkSent
                        self._xasCli.AsyncSendData(b"\r\n", onDataSent=onDataSent)

                    self._xasCli.AsyncSendSendingBuffer(
                        size=len(self._sendingBuf), onDataSent=onChunkDataSent
                    )

                data = ("%x\r\n" % len(self._sendingBuf)).encode()
                self._xasCli.AsyncSendData(data, onDataSent=onChunkHdrSent)
        else:
            self._xasCli.OnClosed = None
            self._xasCli.Close()

    # ------------------------------------------------------------------------

    def _onClosed(self, xasCli, closedReason):
        if self._stream:
            try:
                self._stream.close()
            except Exception as e:
                sys.print_exception(e)
            self._stream = None
        self._sendingBuf = None

    # ------------------------------------------------------------------------

    def _reason(self, code):
        return self._RESPONSE_CODES.get(code, "Unknown reason")

    # ------------------------------------------------------------------------

    def _makeBaseResponseHdr(self, code):
        reason = self._reason(code)
        host = self._request.Host
        host = " to {}".format(host) if host else ""
        _logger.info(
            "from %s:%s%s %s %s >> [%s] %s",
            self._xasCli.CliAddr[0],
            self._xasCli.CliAddr[1],
            host,
            self._request._method,
            self._request._path,
            code,
            reason,
        )
        if self._allow_all_origins:
            self._acAllowOrigin = self._request.Origin
        if self._acAllowOrigin:
            self.SetHeader("Access-Control-Allow-Origin", self._acAllowOrigin)
        self.SetHeader("Server", self._server_name)
        hdr = ""
        for n in self._headers:
            hdr += "%s: %s\r\n" % (n, self._headers[n])
        resp = "HTTP/1.1 %s %s\r\n%s\r\n" % (code, reason, hdr)
        return resp.encode("ISO-8859-1")

    # ------------------------------------------------------------------------

    def _makeResponseHdr(self, code):
        self.SetHeader("Connection", "Close")
        if self._allowCaching:
            self.SetHeader("Cache-Control", "public, max-age=31536000")
        else:
            self.SetHeader("Cache-Control", "no-cache, no-store, must-revalidate")
        if self._contentType:
            ct = self._contentType
            if self._contentCharset:
                ct += "; charset=%s" % self._contentCharset
            self.SetHeader("Content-Type", ct)
        if self._contentLength:
            self.SetHeader("Content-Length", self._contentLength)
        return self._makeBaseResponseHdr(code)

    # ------------------------------------------------------------------------

    def _on_switched(self, xas_cli, _):
        if not self._switch_result:
            return

        self._switch_result(xas_cli.detach_socket())
        self._switch_result = None

    def SwitchingProtocols(self, upgrade, switch_result=None):
        self._switch_result = switch_result
        if not isinstance(upgrade, str) or len(upgrade) == 0:
            raise ValueError('"upgrade" must be a not empty string.')
        if self._hdrSent:
            _logger.warning(
                'response headers already sent for request "%s".', self._request._path
            )
            return
        self.SetHeader("Connection", "Upgrade")
        self.SetHeader("Upgrade", upgrade)
        data = self._makeBaseResponseHdr(101)
        self._xasCli.AsyncSendData(data, self._on_switched)
        self._hdrSent = True

    # ------------------------------------------------------------------------

    def ReturnStream(self, code, stream):
        if not isinstance(code, int) or code <= 0:
            raise ValueError('"code" must be a positive integer.')
        if not hasattr(stream, "readinto") or not hasattr(stream, "close"):
            raise ValueError('"stream" must be a readable buffer protocol object.')
        if self._hdrSent:
            _logger.warning(
                'response headers already sent for request "%s".', self._request._path
            )
            try:
                stream.close()
            except Exception as e:
                sys.print_exception(e)
            return
        if self._request._method != "HEAD":
            self._stream = stream
            self._sendingBuf = memoryview(self._xasCli.SendingBuffer)
            self._xasCli.OnClosed = self._onClosed
        else:
            try:
                stream.close()
            except Exception as e:
                sys.print_exception(e)
        if not self._contentType:
            self._contentType = "application/octet-stream"
        if not self._contentLength:
            self.SetHeader("Transfer-Encoding", "chunked")
        data = self._makeResponseHdr(code)
        self._xasCli.AsyncSendData(data, onDataSent=self._onDataSent)
        self._hdrSent = True

    # ------------------------------------------------------------------------

    # An accept header can contain patterns, e.g. "text/*" but this function only handles the pattern "*/*".
    def _status_code_content(self, code):
        for type in self._request.Accept:
            type = type.rsplit(";", 1)[0]  # Strip ";q=weight".
            if type in ["text/html", "*/*"]:
                content = self._CODE_CONTENT_TMPL.format(
                    code=code, reason=self._reason(code)
                )
                return "text/html", content
            if type == "application/json":
                content = {"code": code, "name": self._reason(code)}
                return "application/json", json.dumps(content)
        return None, None

    def Return(self, code, content=None):
        if not isinstance(code, int) or code <= 0:
            raise ValueError('"code" must be a positive integer.')
        if self._hdrSent:
            _logger.warning(
                'response headers already sent for request "%s".', self._request._path
            )
            return
        if not content:
            (self._contentType, content) = self._status_code_content(code)

        if content:
            if isinstance(content, str):
                content = content.encode("UTF-8")
                if not self._contentType:
                    self._contentType = "text/html"
                self._contentCharset = "UTF-8"
            elif not self._contentType:
                self._contentType = "application/octet-stream"
            self._contentLength = len(content)

        data = self._makeResponseHdr(code)

        if content and self._request._method != "HEAD":
            data += bytes(content)

        self._xasCli.AsyncSendData(data, onDataSent=self._onDataSent)
        self._hdrSent = True

    # ------------------------------------------------------------------------

    def ReturnJSON(self, code, obj):
        if not isinstance(code, int) or code <= 0:
            raise ValueError('"code" must be a positive integer.')
        self._contentType = "application/json"
        try:
            content = json.dumps(obj)
        except:
            raise ValueError('"obj" cannot be converted into JSON format.')
        self.Return(code, content)

    # ------------------------------------------------------------------------

    def ReturnOk(self, content=None):
        self.Return(200, content)

    # ------------------------------------------------------------------------

    def ReturnOkJSON(self, obj):
        self.ReturnJSON(200, obj)

    # ------------------------------------------------------------------------

    def ReturnFile(self, filename, attachmentName=None):
        if not isinstance(filename, str) or len(filename) == 0:
            raise ValueError('"filename" must be a not empty string.')
        if attachmentName is not None and not isinstance(attachmentName, str):
            raise ValueError('"attachmentName" must be a string or None.')
        try:
            size = stat(filename)[6]
        except:
            self.ReturnNotFound()
            return
        try:
            file = open(filename, "rb")
        except:
            self.ReturnForbidden()
            return
        if attachmentName:
            cd = 'attachment; filename="%s"' % attachmentName.replace('"', "'")
            self.SetHeader("Content-Disposition", cd)
        if not self._contentType:
            raise ValueError('"ContentType" must be set')
        self._contentLength = size
        self.ReturnStream(200, file)

    # ------------------------------------------------------------------------

    def ReturnNotModified(self):
        self.Return(304)

    # ------------------------------------------------------------------------

    def ReturnRedirect(self, location):
        if not isinstance(location, str) or len(location) == 0:
            raise ValueError('"location" must be a not empty string.')
        self.SetHeader("Location", location)
        self.Return(307)

    # ------------------------------------------------------------------------

    def ReturnBadRequest(self):
        self.Return(400)

    # ------------------------------------------------------------------------

    def ReturnForbidden(self):
        self.Return(403)

    # ------------------------------------------------------------------------

    def ReturnNotFound(self):
        if self._not_found_url:
            self.ReturnRedirect(self._not_found_url)
        else:
            self.Return(404)

    # ------------------------------------------------------------------------

    def ReturnMethodNotAllowed(self):
        self.Return(405)

    # ------------------------------------------------------------------------

    def ReturnEntityTooLarge(self):
        self.Return(413)

    # ------------------------------------------------------------------------

    def ReturnInternalServerError(self):
        self.Return(500)

    # ------------------------------------------------------------------------

    def ReturnNotImplemented(self):
        self.Return(501)

    # ------------------------------------------------------------------------

    def ReturnServiceUnavailable(self):
        self.Return(503)

    # ------------------------------------------------------------------------

    @property
    def Request(self):
        return self._request

    # ------------------------------------------------------------------------

    @property
    def UserAddress(self):
        return self._xasCli.CliAddr

    # ------------------------------------------------------------------------

    @property
    def AllowCaching(self):
        return self._allowCaching

    @AllowCaching.setter
    def AllowCaching(self, value):
        self._check_value("AllowCaching", value, isinstance(value, bool))
        self._allowCaching = value

    # ------------------------------------------------------------------------

    @property
    def AccessControlAllowOrigin(self):
        return self._acAllowOrigin

    @AccessControlAllowOrigin.setter
    def AccessControlAllowOrigin(self, value):
        self._check_none_or_str("AccessControlAllowOrigin", value)
        self._acAllowOrigin = value

    # ------------------------------------------------------------------------

    @property
    def ContentType(self):
        return self._contentType

    @ContentType.setter
    def ContentType(self, value):
        self._check_none_or_str("ContentType", value)
        self._contentType = value

    # ------------------------------------------------------------------------

    @property
    def ContentCharset(self):
        return self._contentCharset

    @ContentCharset.setter
    def ContentCharset(self, value):
        self._check_none_or_str("ContentCharset", value)
        self._contentCharset = value

    # ------------------------------------------------------------------------

    @property
    def ContentLength(self):
        return self._contentLength

    @ContentLength.setter
    def ContentLength(self, value):
        self._check_value("ContentLength", value, isinstance(value, int) and value >= 0)
        self._contentLength = value

    # ------------------------------------------------------------------------

    @property
    def HeadersSent(self):
        return self._hdrSent

    # ------------------------------------------------------------------------

    def _check_value(self, name, value, condition):
        if not condition:
            raise ValueError('{} is not a valid value for "{}"'.format(value, name))

    def _check_none_or_str(self, name, value):
        self._check_value(name, value, value is None or isinstance(value, str))


# ============================================================================
# ============================================================================
# ============================================================================
