import micropython
import gc

gc.collect()
micropython.mem_info()

from wifi_setup.wifi_setup import WiFiSetup

# You should give every device a unique name (to use as its access point name).
setup = WiFiSetup("ding-5cd80b3")
sta = setup.setup()
del setup
print("WiFi is setup")

gc.collect()
micropython.mem_info()
