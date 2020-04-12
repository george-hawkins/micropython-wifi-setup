import network
import time

from wifi_setup.credentials import Credentials


class WiFiSetup:
    # My ESP32 takes about 2 seconds to join, so 8s is a long timeout.
    _CONNECT_TIMEOUT = 8000

    @staticmethod
    def _default_message(sta):
        return sta.ifconfig()[0]

    # The default `message` function returns the device's IP address but
    # one could provide a function that e.g. returned an MQTT topic ID.
    def __init__(self, essid, message=None):
        self._essid = essid
        # You can't use a static method as a default argument
        # https://stackoverflow.com/a/21672157/245602
        self._message = message if message else self._default_message

        self._credentials = Credentials()
        self._sta = network.WLAN(network.STA_IF)
        self._sta.active(True)

    def setup(self):
        if not self._connect_previous():
            from wifi_setup.captive_portal import portal
            portal(self._essid, self._connect_new)

    def _connect_previous(self):
        ssid, password = self._credentials.get()

        return self._connect(ssid, password) if ssid else False

    def _connect_new(self, ssid, password):
        if not self._connect(ssid, password):
            return None

        self._credentials.put(ssid, password)
        return self._message(self._sta)

    def _connect(self, ssid, password):
        print("attempting to connect to {}".format(ssid))

        # Password may be none if the network is open.
        self._sta.connect(ssid, password)

        if not self._sync_wlan_connect(self._sta):
            print("failed to connect")
            return False

        print("Connected to {} with address {}".format(ssid, self._sta.ifconfig()[0]))
        return True

    # I had hoped I could use wlan.status() to e.g. report if the password was wrong.
    # But with MicroPython 1.12 (and my Ubiquiti UniFi AP AC-PRO) wlan.status() doesn't prove very useful.
    # See https://forum.micropython.org/viewtopic.php?f=18&t=7942
    @staticmethod
    def _sync_wlan_connect(wlan, timeout=_CONNECT_TIMEOUT):
        start = time.ticks_ms()
        while True:
            if wlan.isconnected():
                return True
            diff = time.ticks_diff(time.ticks_ms(), start)
            if diff > timeout:
                wlan.disconnect()
                return False