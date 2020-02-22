import network

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="esp32-5cd80b3", authmode=network.AUTH_OPEN)

# ----------------------------------------------------------------------

from MicroWebSrv2  import *
from time          import sleep

mws2 = MicroWebSrv2()

# Redirect all unfound paths to the root.
mws2.NotFoundURL = '/'

mws2.StartManaged()
#
## Main program loop until keyboard interrupt,
#try :
#    while mws2.IsRunning :
#        sleep(1)
#except KeyboardInterrupt :
#    pass
#
## End,
#print()
#mws2.Stop()
#print('Bye')
#print()
#
## ============================================================================
## ============================================================================
## ============================================================================
