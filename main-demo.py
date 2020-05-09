import micropython
import gc
import select

from slim.slim_server import SlimServer
from slim.fileserver_module import FileserverModule

gc.collect()
micropython.mem_info()

from wifi_setup.wifi_setup import WiFiSetup

# You should give every device a unique name (to use as its access point name).
setup = WiFiSetup("ding-5cd80b3")
sta = setup.connect_or_setup()
del setup
print("WiFi is setup")

gc.collect()
micropython.mem_info()

poller = select.poll()

slim_server = SlimServer(poller)
slim_server.add_module(FileserverModule({ "html": "text/html" }))

while True:
    for (s, event) in poller.ipoll(0):
        slim_server.pump(s, event)
    slim_server.pump_expire()
