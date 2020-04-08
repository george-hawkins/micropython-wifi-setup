# The compiler needs a lot of space to process XAsyncSockets etc. so
# import them first before anything else starts to consume memory.
from slim.micro_web_srv_2.web_route import WebRoute, HttpMethod
from slim.fileserver_module import FileserverModule
from slim.options_module import OptionsModule
from slim.slim_server import SlimServer
from slim.util import print_select_event, access, sync_wlan_connect
from slim.web_route_module import WebRouteModule
from slim.logger import Logger
from slim.slim_config import SlimConfig

import btree
import network
import select

from binascii import hexlify

from schedule import Scheduler, CancelJob


SSID = b"ssid"
PASSWORD = b"password"

f = access("credentials")
db = btree.open(f)

if SSID not in db:
    raise Exception("WiFi credentials have not been configured")
# If this exception occurs, go to the REPL and enter:
# >>> db[SSID] = "My WiFi network"
# >>> db[PASSWORD] = "My WiFi password"
# >>> db.flush()
# And then reset the board.

ssid = db[SSID]
password = db[PASSWORD]

sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(ssid, password)

if not sync_wlan_connect(sta):
    raise Exception(
        "Failed to conntect to {}. Check your password and try again.".format(ssid)
    )

print("Connected to {} with address {}".format(ssid, sta.ifconfig()[0]))

# ----------------------------------------------------------------------


@WebRoute(HttpMethod.GET, "/api/access-points")
def request_access_points(request):
    points = [(p[0], hexlify(p[1])) for p in sta.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/api/access-point")
def request_access_point(request):
    data = request.GetPostedURLEncodedForm()
    print("Data", data)
    bssid = data.get("bssid", None)
    password = data.get("password", None)
    if not bssid or not password:
        request.Response.ReturnBadRequest()
        return

    print("BSSID", bssid)
    print("Password", password)
    request.Response.ReturnOkJSON({"message": "192.168.0.xxx"})


_NO_CONTENT = 204

# If a client specifies a keep-alive period of Xs then they must ping again within Xs plus a fixed "tolerance".
_TOLERANCE = 1


schedule = Scheduler()
timeout_job = None


def timed_out():
    print("Keep-alive timeout expired.")
    # At this point a non-test server would shutdown.
    global timeout_job
    timeout_job = None
    return CancelJob  # Tell scheduler that we want one-shot behavior.


@WebRoute(HttpMethod.POST, "/api/alive")
def request_alive(request):
    data = request.GetPostedURLEncodedForm()
    timeout = data.get("timeout", None)
    if not timeout:
        request.Response.ReturnBadRequest()
        return

    print("Timeout", timeout)
    timeout = int(timeout) + _TOLERANCE
    global timeout_job
    if timeout_job:
        schedule.cancel_job(timeout_job)
    timeout_job = schedule.every(timeout).seconds.do(timed_out)

    request.Response.Return(_NO_CONTENT)


# ----------------------------------------------------------------------


poller = select.poll()

logger = Logger()

config = SlimConfig(logger=logger)

slim_server = SlimServer(config, poller)

slim_server.add_module("webroute", WebRouteModule(logger))
# fmt: off
slim_server.add_module("fileserver", FileserverModule({
    "html": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "woff2": "font/woff2",
    "ico": "image/x-icon",
}))
# fmt: on
slim_server.add_module("options", OptionsModule())

# If no timeout is given `ipoll` blocks and the for-loop goes forever.
# With a timeout the for-loop exits every time the timeout expires.
# I.e. the underlying iterable reports that it has no more elements.
while True:
    # Under the covers polling is done with a non-blocking ioctl call and the timeout
    # (or blocking forever) is implemented with a hard loop, so there's nothing to be
    # gained, e.g. reduced power consumption, by using a timeout greater than 0.
    for (s, event) in poller.ipoll(0):
        # If event has bits other than POLLIN or POLLOUT then print it.
        if event & ~(select.POLLIN | select.POLLOUT):
            print_select_event(event)
        slim_server.pump(s, event)

    # Give things a chance to check for the expiration of timeouts.
    slim_server.pump_expire()
    schedule.run_pending()
