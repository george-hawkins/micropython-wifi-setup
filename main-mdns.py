import network
  
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="esp32-5cd80b3", authmode=network.AUTH_OPEN)

addr = ap.ifconfig()[0]

# ----------------------------------------------------------------------

import select

poller = select.poll()

# ----------------------------------------------------------------------

from microDNSSrv import MicroDNSSrv

mds = MicroDNSSrv()
mds.Start()

addrBytes = MicroDNSSrv._ipV4StrToBytes(addr)

# We answer with our address for _all_ names.
def lookup(domName):
    print('Resolved', domName)
    return addrBytes

poller.register(mds._server, select.POLLIN)

# ----------------------------------------------------------------------

from slimDNS import SlimDNSServer

slimDns = SlimDNSServer(addr)

# Lookup using `dig @224.0.0.251 -p 5353 portal.local`.
# You can add additional names with additional calls to `advertise_hostname`.
slimDns.advertise_hostname("portal")
slimDns.advertise_hostname("dns")

poller.register(slimDns.sock, select.POLLIN)

# ----------------------------------------------------------------------

def printEvent(event):
    if event == select.POLLIN:
        print("IN")
    elif event == select.POLLOUT:
        print("OUT")
    elif event == select.POLLERR:
        print("ERR")
    elif event == select.POLLHUP:
        print("HUP")
    else:
        println("Event", event)

while True:
    for (s, event) in poller.ipoll():
        printEvent(event)

        if event == select.POLLIN:
            if s == slimDns.sock:
                slimDns.process_waiting_packets()
            elif s == mds._server:
                mds.process_request(lookup)

# Currently there's no exit from the while but when there is we need to cleanup...
mds._server.close()
slimDns.sock.close()
