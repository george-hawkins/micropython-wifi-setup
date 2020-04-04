import errno
import select
import time


_POLL_EVENTS = {
    select.POLLIN: "IN",
    select.POLLOUT: "OUT",
    select.POLLHUP: "HUP",
    select.POLLERR: "ERR",
}


def print_select_event(event):
    mask = 1
    while event:
        if event & 1:
            print("Event", _POLL_EVENTS.get(mask, mask))
        event >>= 1
        mask <<= 1


# Open or create a file in binary mode for updating.
def access(filename):
    # Python `open` mode characters are a little non-intuitive.
    # For details see https://docs.python.org/3/library/functions.html#open
    try:
        return open(filename, "r+b")
    except OSError as e:
        if e.args[0] != errno.ENOENT:
            raise e
        print("Creating", filename)
        return open(filename, "w+b")


# My ESP32 takes about 2 seconds to join, so 8s is a long timeout.
_CONNECT_TIMEOUT = 8000


# I had hoped I could use wlan.status() to e.g. report if the password was wrong.
# But with MicroPython 1.12 (and my Ubiquiti UniFi AP AC-PRO) wlan.status() doesn't prove very useful.
# See https://forum.micropython.org/viewtopic.php?f=18&t=7942
def sync_wlan_connect(wlan, timeout=_CONNECT_TIMEOUT):
    start = time.ticks_ms()
    while True:
        if wlan.isconnected():
            return True
        diff = time.ticks_diff(time.ticks_ms(), start)
        if diff > timeout:
            wlan.disconnect()
            return False

