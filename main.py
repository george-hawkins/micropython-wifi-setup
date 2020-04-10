from util import access, sync_wlan_connect

import micropython
import gc
import btree
import network


gc.collect()
micropython.mem_info()


class Credentials:
    _SSID = b"ssid"
    _PASSWORD = b"password"
    _CREDENTIALS = "credentials"

    def __init__(self, filename=_CREDENTIALS):
        self._filename = filename

    def get(self):
        def action(db):
            ssid = db.get(self._SSID)
            password = db.get(self._PASSWORD)

            return (ssid, password) if ssid and password else (None, None)

        return self._db_action(action)

    def put(self, ssid, password):
        def action(db):
            db[self._SSID] = ssid
            db[self._PASSWORD] = password
        self._db_action(action)

    def clear(self):
        def action(db):
            del db[self._SSID]
            del db[self._PASSWORD]
        self._db_action(action)

    def _db_action(self, action):
        with access(self._filename) as f:
            db = btree.open(f)  # Btree doesn't support `with`.
            try:
                return action(db)
            finally:
                # Note that closing the DB does a flush.
                db.close()


class WiFiSetup:
    def __init__(self, essid):
        self._essid = essid

        self._credentials = Credentials()
        self._sta = network.WLAN(network.STA_IF)
        self._sta.active(True)

    def setup(self):
        if not self._connect_previous():
            from connect_portal import portal
            portal(self._essid, self._connect_new)

    def _connect_previous(self):
        ssid, password = self._credentials.get()

        return self._connect(ssid, password) if ssid else False

    def _connect_new(self, ssid, password):
        if not self._connect(ssid, password):
            return None

        self._credentials.put(ssid, password)
        return self._sta.ifconfig()[0]

    def _connect(self, ssid, password):
        print("attempting to connect to {}".format(ssid))

        self._sta.connect(ssid, password)

        if not sync_wlan_connect(self._sta):
            print("failed to connect")
            return False

        print("Connected to {} with address {}".format(ssid, self._sta.ifconfig()[0]))
        return True


# You should give every device a unique name to use as the access point name.
setup = WiFiSetup("ding-5cd80b3")
setup.setup()
del setup

print("WiFi is setup")
gc.collect()
micropython.mem_info()
