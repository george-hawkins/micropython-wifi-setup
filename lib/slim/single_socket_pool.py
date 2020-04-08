import select


# Even without threading we _could_ handle multiple sockets concurrently.
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

    def pump_expire(self):
        if self._async_socket:
            self._async_socket.pump_expire()
