# The MIT License (MIT)
# Copyright 2018 Jean-Christophe Bos & HC2 (www.hc2.fr)

import socket
import sys
import select


class MicroDNSSrv:

    # ============================================================================
    # ===( Utils )================================================================
    # ============================================================================

    @staticmethod
    def ipV4StrToBytes(ipStr):
        try:
            parts = ipStr.split(".")
            if len(parts) == 4:
                return bytes(
                    [int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])]
                )
        except:
            pass
        return None

    # ----------------------------------------------------------------------------

    @staticmethod
    def _getAskedDomainName(packet):
        try:
            queryType = (packet[2] >> 3) & 15
            qCount = (packet[4] << 8) | packet[5]
            if queryType == 0 and qCount == 1:
                pos = 12
                domName = ""
                while True:
                    domPartLen = packet[pos]
                    if domPartLen == 0:
                        break
                    domName += ("." if len(domName) > 0 else "") + packet[
                        pos + 1 : pos + 1 + domPartLen
                    ].decode()
                    pos += 1 + domPartLen
                return domName
        except:
            pass
        return None

    # ----------------------------------------------------------------------------

    @staticmethod
    def _getPacketAnswerA(packet, ipV4Bytes):
        try:
            queryEndPos = 12
            while True:
                domPartLen = packet[queryEndPos]
                if domPartLen == 0:
                    break
                queryEndPos += 1 + domPartLen
            queryEndPos += 5

            return b"".join(
                [
                    packet[:2],  # Query identifier
                    b"\x85\x80",  # Flags and codes
                    packet[4:6],  # Query question count
                    b"\x00\x01",  # Answer record count
                    b"\x00\x00",  # Authority record count
                    b"\x00\x00",  # Additional record count
                    packet[12:queryEndPos],  # Query question
                    b"\xc0\x0c",  # Answer name as pointer
                    b"\x00\x01",  # Answer type A
                    b"\x00\x01",  # Answer class IN
                    b"\x00\x00\x00\x1E",  # Answer TTL 30 secondes
                    b"\x00\x04",  # Answer data length
                    ipV4Bytes,
                ]
            )  # Answer data
        except:
            pass

        return None

    # ============================================================================

    def pump(self, s, event):
        if s != self._server:
            return

        if event != select.POLLIN:
            raise Exception("unexpected event {} on server socket".format(event))

        try:
            packet, cliAddr = self._server.recvfrom(256)
            domName = self._getAskedDomainName(packet)
            if domName:
                domName = domName.lower()
                ipB = self._resolve(domName)
                if ipB:
                    packet = self._getPacketAnswerA(packet, ipB)
                    if packet:
                        self._server.sendto(packet, cliAddr)
        except Exception as e:
            sys.print_exception(e)

    # ============================================================================
    # ===( Constructor )==========================================================
    # ============================================================================

    def __init__(self, resolve, poller, address="", port=53):
        self._resolve = resolve
        self._server = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((address, port))

        poller.register(self._server, select.POLLIN | select.POLLERR | select.POLLHUP)

    def shutdown(self, poller):
        poller.unregister(self._server)
        self._server.close()

    # ============================================================================
    # ============================================================================
    # ============================================================================
