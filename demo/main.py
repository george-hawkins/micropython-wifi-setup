import micropython
import gc
import select

# Display memory available at startup.
gc.collect()
micropython.mem_info()

from wifi_setup.wifi_setup import WiFiSetup

# You should give every device a unique name (to use as its access point name).
ws = WiFiSetup("ding-5cd80b3")
sta = ws.connect_or_setup()
del ws
print("WiFi is setup")

# Display memory available once the WiFi setup process is complete.
gc.collect()
micropython.mem_info()

# Demo that the device is now accessible by starting a web server that serves
# the contents of ./www - just an index.html file that displays a cute ghost.

from slim.slim_server import SlimServer
from slim.fileserver_module import FileserverModule

poller = select.poll()

slim_server = SlimServer(poller)
slim_server.add_module(FileserverModule({"html": "text/html"}))

while True:
    for (s, event) in poller.ipoll(0):
        slim_server.pump(s, event)
    slim_server.pump_expire()
