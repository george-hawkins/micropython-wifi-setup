import network
  
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="esp32-5cd80b3", authmode=network.AUTH_OPEN)

addr = ap.ifconfig()[0]

# ----------------------------------------------------------------------

from microDNSSrv import MicroDNSSrv

MicroDNSSrv.Create( { "*" : addr } )

# ----------------------------------------------------------------------

from slimDNS import SlimDNSServer

server = SlimDNSServer(addr)

# Lookup using `dig -p 5353 portal.local @224.0.0.251`.
# You can add additional names with additional calls to `advertise_hostname`.
server.advertise_hostname("portal")
server.advertise_hostname("mdns")

import select

poller = select.poll()

poller.register(server.sock, select.POLLIN)

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
        if (s == server.sock):
            if event == select.POLLIN:
                server.process_waiting_packets()
