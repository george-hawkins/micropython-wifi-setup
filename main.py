import micropython
import gc

from wifi_setup.wifi_setup import WiFiSetup

gc.collect()
micropython.mem_info()

# You should give every device a unique name to use as its access point name.
setup = WiFiSetup("ding-5cd80b3")
setup.setup()
del setup

print("WiFi is setup")
gc.collect()
micropython.mem_info()
