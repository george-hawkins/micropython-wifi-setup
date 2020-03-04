import errno
import btree
import network
import sys
import time

from socket import socket
import select

# TODO: technically the `.httRequest` and `.libs.X...` aren't requires because of `MicroWebSrv2.__init__`.
from MicroWebSrv2.httpRequest import HttpRequest
from MicroWebSrv2.libs.XAsyncSockets import XBufferSlot, XAsyncTCPClient


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
# >>> db.sync()

ssid = db[SSID]
password = db[PASSWORD]

sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(ssid, password)
while not sta.isconnected():
    time.sleep(1)
print("Connected to {} with address {}".format(ssid, sta.ifconfig()[0]))

# ----------------------------------------------------------------------

server_address = ('0.0.0.0', 80)

server_socket = socket()
server_socket.bind(server_address)

# The backlog argument to `listen` isn't optional for the ESP32 port.
# Internally the backlog is clipped with `LWIP_MIN(LWIP_MAX(backlog, 0), 0xff)`.
LISTEN_MAX = 255

server_socket.listen(LISTEN_MAX)

# ----------------------------------------------------------------------

poller = select.poll()


def print_event(event):
    if event == select.POLLIN:
        print("IN")
    elif event == select.POLLOUT:
        print("OUT")
    elif event == select.POLLERR:
        print("ERR")
    elif event == select.POLLHUP:
        print("HUP")
    else:
        print("Event", event)

# ----------------------------------------------------------------------


class StubbedSocketPool:
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
        poller.unregister(self._async_socket.GetSocketObj())
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
        poller.register(self._async_socket.GetSocketObj(), self._mask)

    def _check(self, async_socket):
        assert self._async_socket == async_socket, "unexpected socket"

    def has_async_socket(self):
        return self._async_socket is not None

    def dispatch(self, s, event):
        if s != self._async_socket.GetSocketObj():
            return

        if event == select.POLLIN:
            self._async_socket.OnReadyForReading()
        elif event == select.POLLOUT:
            self._async_socket.OnReadyForWriting()
        else:
            self._async_socket.OnExceptionalCondition()


# From MicroWebSrv2.__init__
DEFAULT_TIMEOUT = 2  # 2 seconds.


class StubbedMicroServer:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def __init__(self, root="www"):
        self._timeoutSec = DEFAULT_TIMEOUT
        self.AllowAllOrigins = False
        self._modules = {}
        self._root = root

    def Log(self, msg, msg_type):
        print('MWS2-%s> %s' % (msg_type, msg))

    def ResolvePhysicalPath(self, url_path):
        if ".." in url_path:
            return None  # Don't allow trying to escape the root.
        else:
            return self._root + url_path

    def GetMimeTypeFromFilename(self, filename):
        def ext(name):
            partition = name.rpartition(".")
            return None if partition[0] == "" else partition[2].lower()
        return "text/html"


micro_server = StubbedMicroServer()
socket_pool = StubbedSocketPool(poller)

# Slot size from MicroWebSrv2.SetEmbeddedConfig.
SLOT_SIZE = 1024

recv_buf_slot = XBufferSlot(SLOT_SIZE)
send_buf_slot = XBufferSlot(SLOT_SIZE)

while True:
    client_socket, client_address = server_socket.accept()
    try:
        tcp_client = XAsyncTCPClient(socket_pool, client_socket, server_address, client_address,
                                     recv_buf_slot, send_buf_slot)
        request = HttpRequest(micro_server, tcp_client)
        while socket_pool.has_async_socket():
            for (s, event) in poller.ipoll():
                print_event(event)
                socket_pool.dispatch(s, event)
    except Exception as e:
        sys.print_exception(e)
