import network
  
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="esp32-5cd80b3", authmode=network.AUTH_OPEN)

# ----------------------------------------------------------------------

from slimDNS import SlimDNSServer

addr = ap.ifconfig()[0]

# Lookup using `dig -p 5353 gattaca.local @224.0.0.251`.
server = SlimDNSServer(addr, "gattaca")
server.run_forever()
