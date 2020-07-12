# The MIT License (MIT)
# Copyright 2019 Jean-Christophe Bos & HC2 (www.hc2.fr)


import sys
from time import ticks_ms, ticks_diff, ticks_add

import logging


_logger = logging.getLogger("xasync")


# ============================================================================
# ===( XClosedReason )========================================================
# ============================================================================


class XClosedReason:
    Error = 0x00
    ClosedByHost = 0x01
    ClosedByPeer = 0x02
    Timeout = 0x03
    Detached = 0x04


# ============================================================================
# ===( XAsyncSocket )=========================================================
# ============================================================================


class XAsyncSocketException(Exception):
    pass


class XAsyncSocket:
    def __init__(self, asyncSocketsPool, socket, recvBufSlot=None, sendBufSlot=None):
        if type(self) is XAsyncSocket:
            raise XAsyncSocketException(
                "XAsyncSocket is an abstract class and must be implemented."
            )
        self._asyncSocketsPool = asyncSocketsPool
        self._socket = socket
        self._recvBufSlot = recvBufSlot
        self._sendBufSlot = sendBufSlot
        self._expire_time_millis = None
        self._onClosed = None
        try:
            socket.settimeout(0)
            socket.setblocking(0)
            if (recvBufSlot is not None and type(recvBufSlot) is not XBufferSlot) or (
                sendBufSlot is not None and type(sendBufSlot) is not XBufferSlot
            ):
                raise Exception()
            asyncSocketsPool.AddAsyncSocket(self)
        except Exception as e:
            sys.print_exception(e)
            raise XAsyncSocketException("XAsyncSocket : Arguments are incorrects.")

    # ------------------------------------------------------------------------

    def _setExpireTimeout(self, timeoutSec):
        try:
            if timeoutSec and timeoutSec > 0:
                self._expire_time_millis = ticks_add(ticks_ms(), timeoutSec * 1000)
        except:
            raise XAsyncSocketException(
                '"timeoutSec" is incorrect to set expire timeout.'
            )

    # ------------------------------------------------------------------------

    def _removeExpireTimeout(self):
        self._expire_time_millis = None

    # ------------------------------------------------------------------------

    # A subclass can choose to do something on socket expiration.
    def _expired(self):
        pass

    # ------------------------------------------------------------------------

    def pump_expire(self):
        if self._expire_time_millis:
            diff = ticks_diff(ticks_ms(), self._expire_time_millis)
            if diff > 0:
                self._expired()
                self._close(XClosedReason.Timeout)

    # ------------------------------------------------------------------------

    def detach_socket(self):
        socket = self._socket
        if not self._close(XClosedReason.Detached, do_close=False):
            raise XAsyncSocketException("Failed to detach socket")
        return socket

    def _close(
        self, closedReason=XClosedReason.Error, triggerOnClosed=True, do_close=True
    ):
        if self._asyncSocketsPool.RemoveAsyncSocket(self):
            try:
                if do_close:
                    self._socket.close()
            except Exception as e:
                sys.print_exception(e)
            self._socket = None
            if self._recvBufSlot is not None:
                self._recvBufSlot = None
            if self._sendBufSlot is not None:
                self._sendBufSlot = None
            if triggerOnClosed and self._onClosed:
                try:
                    self._onClosed(self, closedReason)
                except Exception as ex:
                    raise XAsyncSocketException(
                        'Error when handling the "OnClose" event : %s' % ex
                    )
            return True
        return False

    # ------------------------------------------------------------------------

    def GetSocketObj(self):
        return self._socket

    # ------------------------------------------------------------------------

    def Close(self):
        return self._close(XClosedReason.ClosedByHost)

    # ------------------------------------------------------------------------

    def OnReadyForReading(self):
        pass

    # ------------------------------------------------------------------------

    def OnReadyForWriting(self):
        pass

    # ------------------------------------------------------------------------

    def OnExceptionalCondition(self):
        self._close()

    # ------------------------------------------------------------------------

    @property
    def ExpireTimeSec(self):
        return self._expire_time_millis / 1000

    @property
    def OnClosed(self):
        return self._onClosed

    @OnClosed.setter
    def OnClosed(self, value):
        self._onClosed = value


# ============================================================================
# ===( XAsyncTCPClient )======================================================
# ============================================================================


class XAsyncTCPClientException(Exception):
    pass


class XAsyncTCPClient(XAsyncSocket):
    def __init__(self, asyncSocketsPool, cliSocket, cliAddr, recvBufSlot, sendBufSlot):
        try:
            super().__init__(asyncSocketsPool, cliSocket, recvBufSlot, sendBufSlot)
            self._cliAddr = cliAddr if cliAddr else ("0.0.0.0", 0)
            self._onFailsToConnect = None
            self._onConnected = None
            self._onDataRecv = None
            self._onDataRecvArg = None
            self._onDataSent = None
            self._onDataSentArg = None
            self._sizeToRecv = None
            self._rdLinePos = None
            self._rdLineEncoding = None
            self._rdBufView = None
            self._wrBufView = None
        except Exception as e:
            sys.print_exception(e)
            raise XAsyncTCPClientException(
                "Error to creating XAsyncTCPClient, arguments are incorrects."
            )

    # ------------------------------------------------------------------------

    def _expired(self):
        # This actually happens regularly. It seems to be a speed trick used by browsers,
        # they open multiple concurrent connections in _anticipation_ of needing them for
        # additional requests, e.g. as a page loads. Some of these connections are never
        # used and this eventually triggers the expiration logic here.
        _logger.debug(
            "connection from %s:%s expired", self._cliAddr[0], self._cliAddr[1]
        )

    # ------------------------------------------------------------------------

    def Close(self):
        if self._wrBufView:
            try:
                self._socket.send(self._wrBufView)
            except Exception as e:
                sys.print_exception(e)
        return self._close(XClosedReason.ClosedByHost)

    # ------------------------------------------------------------------------

    def OnReadyForReading(self):
        while True:
            if self._rdLinePos is not None:
                # In the context of reading a line,
                while True:
                    try:
                        try:
                            b = self._socket.recv(1)
                        except BlockingIOError as bioErr:
                            if bioErr.errno != 35:
                                self._close()
                            return
                        except:
                            self._close()
                            return
                    except:
                        self._close()
                        return
                    if b:
                        if b == b"\n":
                            lineLen = self._rdLinePos
                            self._rdLinePos = None
                            self._asyncSocketsPool.NotifyNextReadyForReading(
                                self, False
                            )
                            self._removeExpireTimeout()
                            if self._onDataRecv:
                                line = self._recvBufSlot.Buffer[:lineLen]
                                try:
                                    line = bytes(line).decode(self._rdLineEncoding)
                                except:
                                    line = None
                                try:
                                    self._onDataRecv(self, line, self._onDataRecvArg)
                                except Exception as ex:
                                    sys.print_exception(ex)
                                    raise XAsyncTCPClientException(
                                        'Error when handling the "OnDataRecv" event : %s'
                                        % ex
                                    )
                            return
                        elif b != b"\r":
                            if self._rdLinePos < self._recvBufSlot.Size:
                                self._recvBufSlot.Buffer[self._rdLinePos] = ord(b)
                                self._rdLinePos += 1
                            else:
                                self._close()
                                return
                    else:
                        self._close(XClosedReason.ClosedByPeer)
                        return
            elif self._sizeToRecv:
                # In the context of reading data,
                recvBuf = self._rdBufView[-self._sizeToRecv :]
                try:
                    try:
                        n = self._socket.recv_into(recvBuf)
                    except BlockingIOError as bioErr:
                        if bioErr.errno != 35:
                            self._close()
                        return
                    except:
                        self._close()
                        return
                except:
                    try:
                        n = self._socket.readinto(recvBuf)
                    except:
                        self._close()
                        return
                if not n:
                    self._close(XClosedReason.ClosedByPeer)
                    return
                self._sizeToRecv -= n
                if not self._sizeToRecv:
                    data = self._rdBufView
                    self._rdBufView = None
                    self._asyncSocketsPool.NotifyNextReadyForReading(self, False)
                    self._removeExpireTimeout()
                    if self._onDataRecv:
                        try:
                            self._onDataRecv(self, data, self._onDataRecvArg)
                        except Exception as ex:
                            raise XAsyncTCPClientException(
                                'Error when handling the "OnDataRecv" event : %s' % ex
                            )
                    return
            else:
                return

    # ------------------------------------------------------------------------

    def OnReadyForWriting(self):
        if self._wrBufView:
            try:
                n = self._socket.send(self._wrBufView)
            except:
                return
            self._wrBufView = self._wrBufView[n:]
            if not self._wrBufView:
                self._asyncSocketsPool.NotifyNextReadyForWriting(self, False)
                if self._onDataSent:
                    try:
                        self._onDataSent(self, self._onDataSentArg)
                    except Exception as ex:
                        raise XAsyncTCPClientException(
                            'Error when handling the "OnDataSent" event : %s' % ex
                        )

    # ------------------------------------------------------------------------

    def AsyncRecvLine(
        self, lineEncoding="UTF-8", onLineRecv=None, onLineRecvArg=None, timeoutSec=None
    ):
        if self._rdLinePos is not None or self._sizeToRecv:
            raise XAsyncTCPClientException(
                "AsyncRecvLine : Already waiting asynchronous receive."
            )
        if self._socket:
            self._setExpireTimeout(timeoutSec)
            self._rdLinePos = 0
            self._rdLineEncoding = lineEncoding
            self._onDataRecv = onLineRecv
            self._onDataRecvArg = onLineRecvArg
            self._asyncSocketsPool.NotifyNextReadyForReading(self, True)
            return True
        return False

    # ------------------------------------------------------------------------

    def AsyncRecvData(
        self, size=None, onDataRecv=None, onDataRecvArg=None, timeoutSec=None
    ):
        if self._rdLinePos is not None or self._sizeToRecv:
            raise XAsyncTCPClientException(
                "AsyncRecvData : Already waiting asynchronous receive."
            )
        if self._socket:
            if size is None:
                size = self._recvBufSlot.Size
            elif not isinstance(size, int) or size <= 0:
                raise XAsyncTCPClientException('AsyncRecvData : "size" is incorrect.')
            if size <= self._recvBufSlot.Size:
                self._rdBufView = memoryview(self._recvBufSlot.Buffer)[:size]
            else:
                try:
                    self._rdBufView = memoryview(bytearray(size))
                except:
                    raise XAsyncTCPClientException(
                        "AsyncRecvData : No enought memory to receive %s bytes." % size
                    )
            self._setExpireTimeout(timeoutSec)
            self._sizeToRecv = size
            self._onDataRecv = onDataRecv
            self._onDataRecvArg = onDataRecvArg
            self._asyncSocketsPool.NotifyNextReadyForReading(self, True)
            return True
        return False

    # ------------------------------------------------------------------------

    def AsyncSendData(self, data, onDataSent=None, onDataSentArg=None):
        if self._socket:
            try:
                if bytes([data[0]]):
                    if self._wrBufView:
                        self._wrBufView = memoryview(bytes(self._wrBufView) + data)
                    else:
                        self._wrBufView = memoryview(data)
                    self._onDataSent = onDataSent
                    self._onDataSentArg = onDataSentArg
                    self._asyncSocketsPool.NotifyNextReadyForWriting(self, True)
                    return True
            except Exception as e:
                sys.print_exception(e)
            raise XAsyncTCPClientException('AsyncSendData : "data" is incorrect.')
        return False

    # ------------------------------------------------------------------------

    def AsyncSendSendingBuffer(self, size=None, onDataSent=None, onDataSentArg=None):
        if self._wrBufView:
            raise XAsyncTCPClientException(
                "AsyncSendBufferSlot : Already waiting to send data."
            )
        if self._socket:
            if size is None:
                size = self._sendBufSlot.Size
            if size > 0 and size <= self._sendBufSlot.Size:
                self._wrBufView = memoryview(self._sendBufSlot.Buffer)[:size]
                self._onDataSent = onDataSent
                self._onDataSentArg = onDataSentArg
                self._asyncSocketsPool.NotifyNextReadyForWriting(self, True)
                return True
        return False

    # ------------------------------------------------------------------------

    @property
    def CliAddr(self):
        return self._cliAddr

    @property
    def SendingBuffer(self):
        return self._sendBufSlot.Buffer

    @property
    def OnFailsToConnect(self):
        return self._onFailsToConnect

    @OnFailsToConnect.setter
    def OnFailsToConnect(self, value):
        self._onFailsToConnect = value

    @property
    def OnConnected(self):
        return self._onConnected

    @OnConnected.setter
    def OnConnected(self, value):
        self._onConnected = value


# ============================================================================
# ===( XBufferSlot )==========================================================
# ============================================================================


class XBufferSlot:
    def __init__(self, size):
        self._size = size
        self._buffer = bytearray(size)

    @property
    def Size(self):
        return self._size

    @property
    def Buffer(self):
        return self._buffer


# ============================================================================
# ============================================================================
# ============================================================================
