import select
import socket
import logging

from micro_web_srv_2.http_request import HttpRequest
from micro_web_srv_2.libs.xasync_sockets import XBufferSlot, XAsyncTCPClient
from slim.single_socket_pool import SingleSocketPool
from slim.slim_config import SlimConfig

_logger = logging.getLogger("server")


class SlimServer:
    RESPONSE_PENDING = object()

    # The backlog argument to `listen` isn't optional for the ESP32 port.
    # Internally any passed in backlog value is clipped to a maximum of 255.
    _LISTEN_MAX = 255

    # Slot size from MicroWebSrv2.SetEmbeddedConfig.
    _SLOT_SIZE = 1024

    # Python uses "" to refer to INADDR_ANY, i.e. all interfaces.
    def __init__(self, poller, address="", port=80, config=SlimConfig()):
        self._config = config
        self._server_socket = self._create_server_socket(address, port)

        poller.register(
            self._server_socket, select.POLLIN | select.POLLERR | select.POLLHUP
        )

        self._socket_pool = SingleSocketPool(poller)

        self._modules = []
        self._recv_buf_slot = XBufferSlot(self._SLOT_SIZE)
        self._send_buf_slot = XBufferSlot(self._SLOT_SIZE)

    def shutdown(self, poller):
        poller.unregister(self._server_socket)
        self._server_socket.close()

    def add_module(self, instance):
        self._modules.append(instance)

    def _process_request_modules(self, request):
        for modInstance in self._modules:
            try:
                r = modInstance.OnRequest(request)
                if r is self.RESPONSE_PENDING or request.Response.HeadersSent:
                    return
            except Exception as ex:
                name = type(modInstance).__name__
                _logger.error(
                    'Exception in request handler of module "%s" (%s).', name, ex
                )

        request.Response.ReturnNotImplemented()

    def _create_server_socket(self, address, port):
        server_socket = socket.socket()

        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                self._socket_pool,
                client_socket,
                client_address,
                self._recv_buf_slot,
                self._send_buf_slot,
            )
            # HttpRequest registers itself to receive data via tcp_client and once
            # it's read the request, it calls the given process_request callback.
            HttpRequest(
                self._config, tcp_client, process_request=self._process_request_modules
            )
        else:  # Else process the existing request.
            self._socket_pool.pump(s, event)

    def pump_expire(self):
        self._socket_pool.pump_expire()
