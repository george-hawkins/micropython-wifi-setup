from wifi_setup.wifi_setup import WiFiSetup

# You should give every device a unique name (to use as its access point name).
ws = WiFiSetup("ding-5cd80b3")
sta = ws.connect_or_setup()
del ws
print("WiFi is setup")
