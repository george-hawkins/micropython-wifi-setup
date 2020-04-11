# The compiler needs a lot of space to process the server classes etc. so
# import them first before anything else starts to consume memory.
from micro_dns_srv import MicroDNSSrv
from slim.fileserver_module import FileserverModule
from slim.options_module import OptionsModule
from slim.slim_config import SlimConfig
from slim.slim_server import SlimServer
from slim.web_route_module import WebRouteModule
from micro_web_srv_2.web_route import WebRoute, HttpMethod

from util import print_select_event

import network
import select

from binascii import hexlify

from schedule import Scheduler, CancelJob

_ap = network.WLAN(network.AP_IF)

_schedule = Scheduler()

_connect = None
_alive = True

# A captive portal tries to push clients to a login page. This is typically done by
# redirecting all DNS requests to the captive portal web server and then all HTTP
# requests to the login page.
# For an end user, trying to access a web page and then being redirected to a login page
# is a bit confusing so most browsers and OSes these days try to detect this upfront and
# immediately present the login page. For an example of how this is done, see:
# https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection

# Rather than present a login page, this is a captive portal that lets you configure
# access to your network.
def portal(essid, connect):
    global _connect
    _connect = connect
    _ap.active(True)
    _ap.config(essid=essid)  # You can't set values before calling active.

    poller = select.poll()

    # Rather than a 404 (Not Found) response redirect all not found requests to "/".
    config = SlimConfig(not_found_url="/")

    slim_server = SlimServer(poller, config=config)

    slim_server.add_module("webroute", WebRouteModule())
    # fmt: off
    slim_server.add_module("fileserver", FileserverModule({
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
        "woff2": "font/woff2",
        "ico": "image/x-icon",
        "svg": "image/svg+xml"
    }))
    # fmt: on
    slim_server.add_module("options", OptionsModule())

    addr = _ap.ifconfig()[0]
    addrBytes = MicroDNSSrv.ipV4StrToBytes(addr)

    def resolve(name):
        print("Resolving", name)
        return addrBytes

    dns = MicroDNSSrv(resolve, poller)

    # If no timeout is given `ipoll` blocks and the for-loop goes forever.
    # With a timeout the for-loop exits every time the timeout expires.
    # I.e. the underlying iterable reports that it has no more elements.
    while _alive:
        # Under the covers polling is done with a non-blocking ioctl call and the timeout
        # (or blocking forever) is implemented with a hard loop, so there's nothing to be
        # gained, e.g. reduced power consumption, by using a timeout greater than 0.
        for (s, event) in poller.ipoll(0):
            # If event has bits other than POLLIN or POLLOUT then print it.
            if event & ~(select.POLLIN | select.POLLOUT):
                print_select_event(event)
            slim_server.pump(s, event)
            dns.pump(s, event)

        slim_server.pump_expire()  # Expire inactive client sockets.
        _schedule.run_pending()

    _ap.active(False)


@WebRoute(HttpMethod.GET, "/api/access-points")
def request_access_points(request):
    # Tuples are  of the form (SSID, BSSID, channel, RSSI, authmode, hidden).
    points = [(p[0], p[3], p[4]) for p in _ap.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/api/access-point")
def request_access_point(request):
    data = request.GetPostedURLEncodedForm()
    print("Data", data)
    ssid = data.get("ssid", None)
    if not ssid:
        request.Response.ReturnBadRequest()
        return

    password = data.get("password", None)

    result = _connect(ssid, password)
    if not result:
        request.Response.ReturnForbidden()
    else:
        request.Response.ReturnOkJSON({"message": result})


_NO_CONTENT = 204

# If a client specifies a keep-alive period of Xs then they must ping again within Xs plus a fixed "tolerance".
_TOLERANCE = 1


timeout_job = None


def timed_out():
    print("Keep-alive timeout expired.")
    global _alive
    _alive = False
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
        _schedule.cancel_job(timeout_job)
    timeout_job = _schedule.every(timeout).seconds.do(timed_out)

    request.Response.Return(_NO_CONTENT)


print("Loaded", __file__)
