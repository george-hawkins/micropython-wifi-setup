import select
from collections import OrderedDict
from socket import socket

from slim.MicroWebSrv2.httpRequest import HttpRequest
from slim.MicroWebSrv2.libs.XAsyncSockets import XBufferSlot, XAsyncTCPClient
from slim.single_socket_pool import SingleSocketPool
from slim.webserver import slim_server


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
            #  Be careful - this about time.ticks_diff (under the covers ExpireTimeSec involves time.ticks_ms / 1000).
            self._socket_pool.pump(s, event)