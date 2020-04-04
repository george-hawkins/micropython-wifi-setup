# The compiler needs a lot of space to process XAsyncSockets etc. so
# import them first before anything else starts to consume memory.
from slim.MicroWebSrv2.webRoute import WebRoute, HttpMethod
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

@WebRoute(HttpMethod.GET, "/access-points", "Access Points")
def request_access_points(request):
    points = [(p[0], hexlify(p[1])) for p in sta.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/authenticate", "Authenticate")
def request_authenticate(request):
    data = request.GetPostedURLEncodedForm()
    print("Data", data)
    bssid = data.get("bssid", None)
    password = data.get("password", None)
    if bssid is None or password is None:
        request.Response.ReturnBadRequest()
    else:
        print("BSSID", bssid)
        print("Password", password)
        request.Response.ReturnOk()


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
}))
# fmt: on
slim_server.add_module("options", OptionsModule())

while True:
    for (s, event) in poller.ipoll():
        # If event has bits other than POLLIN or POLLOUT then print it.
        if event & ~(select.POLLIN | select.POLLOUT):
            print_select_event(event)
        slim_server.pump(s, event)
