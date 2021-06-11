import network
import time
import logging

from wifi_setup.credentials import Credentials


_logger = logging.getLogger("wifi_setup")


class WiFiSetup:
    # My ESP32 takes about 2 seconds to join, so 8s is a long timeout.
    _CONNECT_TIMEOUT = 8000

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
        self.captive_timeout = None

    def has_ssid(self):
        return self._credentials.get()[0] is not None

    def connect(self):
        ssid, password = self._credentials.get()

        return self._sta if ssid and self._connect(ssid, password) else None

    def setup(self):
        from wifi_setup.captive_portal import CaptivePortal

        # `run` will only return once WiFi is setup.
        CaptivePortal().run(
            self._essid, self._connect_new, captive_timeout=self.captive_timeout
        )

        return self._sta

    def connect_or_setup(self):
        if not self.connect():
            self.setup()

        return self._sta

    @staticmethod
    def clear():
        Credentials().clear()

    def _connect_new(self, ssid, password):
        if not self._connect(ssid, password):
            return None

        self._credentials.put(ssid, password)
        return self._message(self._sta)

    @staticmethod
    def _default_message(sta):
        return sta.ifconfig()[0]

    def _connect(self, ssid, password):
        _logger.info("attempting to connect to %s", ssid)

        # Now use the ESSID, i.e. the temporary access point name, as the device
        # hostname when making the DHCP request. MicroPython will then also
        # advertise this name using mDNS and you should be able to access the
        # device as <hostname>.local.
        self._sta.config(dhcp_hostname=self._essid)

        # Password may be none if the network is open.
        self._sta.connect(ssid, password)

        if not self._sync_wlan_connect(self._sta):
            _logger.error("failed to connect to %s", ssid)
            return False

        _logger.info("connected to %s with address %s", ssid, self._sta.ifconfig()[0])
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
