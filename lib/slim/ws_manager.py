import select
import socket
import sys
import websocket

from hashlib import sha1
from binascii import b2a_base64

from logging import getLogger


_logger = getLogger("ws_manager")


class WsManager:
    _WS_SPEC_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # See https://stackoverflow.com/a/13456048/245602

    def __init__(self, poller, message_extractor, message_handler):
        self._poller = poller
        self._message_extractor = message_extractor
        self._message_handler = message_handler
        self._clients = {}

    def pump_ws_clients(self, s, event):
        if not isinstance(s, socket.socket):
            return
        fileno = s.fileno()
        if fileno not in self._clients:
            return
        if event != select.POLLIN:
            _logger.warning("unexpected event {} on socket {}".format(event, fileno))
            self._remove_ws_client(fileno)
            return
        ws_client = self._clients[fileno]
        try:
            message = self._message_extractor(ws_client.ws.readinto)
        except Exception as e:
            sys.print_exception(e)
            self._remove_ws_client(fileno)
            return
        if message:
            print(message)
            self._message_handler(message)

    def _remove_ws_client(self, fileno):
        self._clients.pop(fileno).close(self._poller)

    def _add_ws_client(self, client_socket):
        ws_client = _WsClient(self._poller, client_socket)
        self._clients[ws_client.fileno] = ws_client

    def upgrade_connection(self, request):
        key = request.GetHeader("Sec-Websocket-Key")
        if not key:
            return False

        sha = sha1(key.encode())
        sha.update(self._WS_SPEC_GUID)
        accept = b2a_base64(sha.digest()).decode()[:-1]
        request.Response.SetHeader("Sec-WebSocket-Accept", accept)
        request.Response.SwitchingProtocols("websocket", self._add_ws_client)
        return True


class _WsClient:
    def __init__(self, poller, client_socket):
        self._socket = client_socket
        self.ws = websocket.websocket(client_socket, True)
        self.fileno = client_socket.fileno()
        # poller.register doesn't complain if you register ws but it fails when you call ipoll.
        poller.register(client_socket, select.POLLIN | select.POLLERR | select.POLLHUP)

    def close(self, poller):
        poller.unregister(self._socket)
        try:
            self.ws.close()
        except:  # noqa: E722
            pass
