# The compiler needs a lot of space to process XAsyncSockets etc. so
# import them first before anything else starts to consume memory.
from slim.MicroWebSrv2.libs.XAsyncSockets import XBufferSlot, XAsyncTCPClient
from slim.MicroWebSrv2.httpRequest import HttpRequest
from slim.MicroWebSrv2.webRoute import WebRoute, HttpMethod, ResolveRoute
from slim.logger import Logger
from slim.slimConfig import SlimConfig

import errno
import btree
import network
import time
import select

from binascii import hexlify
from os import stat
from socket import socket
from collections import OrderedDict


# Open or create a file in binary mode for updating.
def access(filename):
    # Python `open` mode characters are a little non-intuitive.
    # For details see https://docs.python.org/3/library/functions.html#open
    try:
        return open(filename, "r+b")
    except OSError as e:
        if e.args[0] != errno.ENOENT:
            raise e
        print("Creating", filename)
        return open(filename, "w+b")


SSID = b"ssid"
PASSWORD = b"password"

f = access("credentials")
db = btree.open(f)

if SSID not in db:
    raise Exception("WiFi credentials have not been configured")
# If this exception occurs, go to the REPL and enter:
# >>> db[SSID] = "My WiFi network"
# >>> db[PASSWORD] = "My WiFi password"
# >>> db.flush()
# And then reset the board.

ssid = db[SSID]
password = db[PASSWORD]

# My ESP32 takes about 2 seconds to join, so 8s is a long timeout.
_CONNECT_TIMEOUT = 8000


# I had hoped I could use wlan.status() to e.g. report if the password was wrong.
# But with MicroPython 1.12 (and my Ubiquiti UniFi AP AC-PRO) wlan.status() doesn't prove very useful.
# See https://forum.micropython.org/viewtopic.php?f=18&t=7942
def sync_connect(wlan, timeout=_CONNECT_TIMEOUT):
    start = time.ticks_ms()
    while True:
        if wlan.isconnected():
            return True
        diff = time.ticks_diff(time.ticks_ms(), start)
        if diff > timeout:
            wlan.disconnect()
            return False


sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(ssid, password)

if not sync_connect(sta):
    raise Exception(
        "Failed to conntect to {}. Check your password and try again.".format(ssid)
    )

print("Connected to {} with address {}".format(ssid, sta.ifconfig()[0]))

# ----------------------------------------------------------------------

@WebRoute(HttpMethod.GET, "/access-points", "Access Points")
def request_access_points(request):
    points = [(p[0], hexlify(p[1])) for p in sta.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/authenticate", "Authenticate")
def request_authenticate(request):
    data = request.GetPostedURLEncodedForm()
    print("Data", data)
    bssid = data.get("bssid", None)
    password = data.get("password", None)
    if bssid is None or password is None:
        request.Response.ReturnBadRequest()
    else:
        print("BSSID", bssid)
        print("Password", password)
        request.Response.ReturnOk()


# ----------------------------------------------------------------------

poller = select.poll()

pollEvents = {
    select.POLLIN: "IN",
    select.POLLOUT: "OUT",
    select.POLLHUP: "HUP",
    select.POLLERR: "ERR",
}


def print_select_event(event):
    mask = 1
    while event:
        if event & 1:
            print("Event", pollEvents.get(mask, mask))
        event >>= 1
        mask <<= 1


# ----------------------------------------------------------------------


# Even without threading we could handle multiple sockets concurrently.
# However this socket pool handles only a single socket at a time in order to avoid the
# memory overhead of needing more than one send and receive XBufferSlot at a time.
class SingleSocketPool:
    def __init__(self, poller):
        self._poller = poller
        self._async_socket = None
        self._mask = 0

    def AddAsyncSocket(self, async_socket):
        assert self._async_socket is None, "previous socket has not yet been removed"
        self._mask = select.POLLERR | select.POLLHUP
        self._async_socket = async_socket

    def RemoveAsyncSocket(self, async_socket):
        self._check(async_socket)
        self._poller.unregister(self._async_socket.GetSocketObj())
        self._async_socket = None
        return True  # Caller XAsyncSocket._close will close the underlying socket.

    def NotifyNextReadyForReading(self, async_socket, notify):
        self._check(async_socket)
        self._update(select.POLLIN, notify)

    def NotifyNextReadyForWriting(self, async_socket, notify):
        self._check(async_socket)
        self._update(select.POLLOUT, notify)

    def _update(self, event, set):
        if set:
            self._mask |= event
        else:
            self._mask &= ~event
        self._poller.register(self._async_socket.GetSocketObj(), self._mask)

    def _check(self, async_socket):
        assert self._async_socket == async_socket, "unexpected socket"

    def has_async_socket(self):
        return self._async_socket is not None

    def pump(self, s, event):
        if s != self._async_socket.GetSocketObj():
            return

        if event & select.POLLIN:
            event &= ~select.POLLIN
            self._async_socket.OnReadyForReading()

        if event & select.POLLOUT:
            event &= ~select.POLLOUT
            self._async_socket.OnReadyForWriting()

        # If there are still bits left in event...
        if event:
            self._async_socket.OnExceptionalCondition()


# ----------------------------------------------------------------------

# In CPython S_IFDIR etc. are available via os.stat.
S_IFDIR = 1 << 14


# Neither os.path nor pathlib exist in MicroPython 1.12.
def exists(path):
    try:
        stat(path)
        return True
    except:
        return False


def is_dir(path):
    return stat(path)[0] & S_IFDIR != 0


# ----------------------------------------------------------------------


class SlimServer:
    RESPONSE_PENDING = object()

    # The backlog argument to `listen` isn't optional for the ESP32 port.
    # Internally any passed in backlog value is clipped to a maximum of 255.
    _LISTEN_MAX = 255

    # Slot size from MicroWebSrv2.SetEmbeddedConfig.
    _SLOT_SIZE = 1024

    # Python uses "" to refer to INADDR_ANY, i.e. all interfaces.
    def __init__(self, config, poller, address="", port=80):
        self._config = config
        self._logger = config.logger
        self._server_socket = self._create_server_socket(address, port)

        poller.register(self._server_socket, select.POLLIN | select.POLLERR | select.POLLHUP)

        self._socket_pool = SingleSocketPool(poller)

        # Modules should be processed in the order that they're added so use OrderedDict.
        self._modules = OrderedDict()
        self._recv_buf_slot = XBufferSlot(self._SLOT_SIZE)
        self._send_buf_slot = XBufferSlot(self._SLOT_SIZE)

    def add_module(self, name, instance):
        self._modules[name] = instance

    def process_request_modules(self, request):
        for modName, modInstance in self._modules.items():
            try:
                r = modInstance.OnRequest(request)
                if r is self.RESPONSE_PENDING or request.Response.HeadersSent:
                    return
            except Exception as ex:
                self._logger.error(
                    'Exception in request handler of module "%s" (%s).' % (modName, ex)
                )

        request.Response.ReturnNotImplemented()

    def _create_server_socket(self, address, port):
        server_socket = socket()

        server_socket.bind((address, port))
        server_socket.listen(self._LISTEN_MAX)

        return server_socket

    def pump(self, s, event):
        # If not already processing a request, see if a new request has come in.
        if not self._socket_pool.has_async_socket():
            if s != self._server_socket:
                return

            if event != select.POLLIN:
                raise Exception("unexpected event {} on server socket".format(event))

            client_socket, client_address = self._server_socket.accept()

            # XAsyncTCPClient adds itself to _socket_pool (via the ctor of its parent XAsyncSocket).
            tcp_client = XAsyncTCPClient(
                self._socket_pool, client_socket, client_address, self._recv_buf_slot, self._send_buf_slot
            )
            # HttpRequest registers itself to receive data via tcp_client and once
            # it's read the request, it calls the given process_request callback.
            HttpRequest(
                self._config, tcp_client, process_request=slim_server.process_request_modules
            )
        else:  # Else process the existing request.
            # TODO: add in time-out logic. See lines 115 and 133 onward in
            #  https://github.com/jczic/MicroWebSrv2/blob/d8663f6/MicroWebSrv2/libs/XAsyncSockets.py
            self._socket_pool.pump(s, event)

# ----------------------------------------------------------------------

class FileserverModule:
    _DEFAULT_PAGE = "index.html"

    def __init__(self, mime_types, root="www"):
        self._mime_types = mime_types
        self._root = root

    def OnRequest(self, request):
        if request.IsUpgrade or request.Method not in ("GET", "HEAD"):
            return

        filename = self._resolve_physical_path(request.Path)
        if filename:
            ct = self._get_mime_type_from_filename(filename)
            if ct:
                request.Response.AllowCaching = True
                request.Response.ContentType = ct
                request.Response.ReturnFile(filename)
            else:
                request.Response.ReturnForbidden()
        else:
            request.Response.ReturnNotFound()

    def _resolve_physical_path(self, url_path):
        if ".." in url_path:
            return None  # Don't allow trying to escape the root.

        if url_path.endswith("/"):
            url_path = url_path[:-1]
        path = self._root + url_path
        if exists(path) and is_dir(path):
            path = path + "/" + self._DEFAULT_PAGE

        return path if exists(path) else None

    def _get_mime_type_from_filename(self, filename):
        def ext(name):
            partition = name.rpartition(".")
            return None if partition[0] == "" else partition[2].lower()

        return self._mime_types.get(ext(filename), None)


class WebRoutesModule:
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


class OptionsModule:
    def __init__(self, cors_allow_all=False):
        self._cors_allow_all = cors_allow_all

    def OnRequest(self, request):
        if request.IsUpgrade or request.Method != "OPTIONS":
            return

        if self._cors_allow_all:
            request.Response.SetHeader("Access-Control-Allow-Methods", "*")
            request.Response.SetHeader("Access-Control-Allow-Headers", "*")
            request.Response.SetHeader("Access-Control-Allow-Credentials", "true")
            request.Response.SetHeader("Access-Control-Max-Age", "86400")
        request.Response.ReturnOk()


logger = Logger()

config = SlimConfig(logger=logger)

slim_server = SlimServer(config, poller)

slim_server.add_module("webroute", WebRoutesModule(logger))
# fmt: off
slim_server.add_module("fileserver", FileserverModule({
    "html": "text/html",
    "css": "text/css",
    "js": "application/javascript",
}))
# fmt: on
slim_server.add_module("options", OptionsModule())

while True:
    for (s, event) in poller.ipoll():
        # If event has bits other than POLLIN or POLLOUT then print it.
        if event & ~(select.POLLIN | select.POLLOUT):
            print_select_event(event)
        slim_server.pump(s, event)
