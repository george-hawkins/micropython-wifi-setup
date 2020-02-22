import network

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="esp32-5cd80b3", authmode=network.AUTH_OPEN)

# ----------------------------------------------------------------------

from microDNSSrv import MicroDNSSrv

addr = ap.ifconfig()[0]

MicroDNSSrv.Create( { "*" : addr } )

# ----------------------------------------------------------------------

from MicroWebSrv2  import *
from time          import sleep

mws2 = MicroWebSrv2()

# Reduce slot count as memory is at a minimum.
mws2.BufferSlotsCount = 8

# Redirect all unfound paths to the root.
mws2.NotFoundURL = '/'

mws2.StartManaged()
