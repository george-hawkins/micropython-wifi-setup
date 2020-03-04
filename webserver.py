from socket import socket

addr = ('0.0.0.0', 80)

server = socket()
server.bind(addr)

server.listen()

print('listening on', addr)

from MicroWebSrv2 import httpRequest

while True:
    client, client_addr = server.accept()
    client_file = client.makefile('rwb')
    request = httpRequest(None, None)
    while True:
        # There seems to be no way to get `readline` to timeout - to be robust polling should be used.
        line = client_file.readline()
        if not line or line == b'\r\n':
            break
        print('>', line)
    client.send(b"HTTP/1.0 204 No Content\r\n\r\n")
    client.close()
