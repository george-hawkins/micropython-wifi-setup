# The compiler needs a lot of space to process the server classes etc. so
# import them first before anything else starts to consume memory.
from slim.fileserver_module import FileserverModule
from slim.options_module import OptionsModule
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


# A captive portal that lets you configure access to your network.
def portal(essid, connect):
    global _connect
    _connect = connect
    _ap.active(True)
    _ap.config(essid=essid)  # You can't set values before calling active.

    poller = select.poll()

    slim_server = SlimServer(poller)

    slim_server.add_module("webroute", WebRouteModule())
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
    while _alive:
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
        _schedule.run_pending()

    _ap.active(False)


@WebRoute(HttpMethod.GET, "/api/access-points")
def request_access_points(request):
    points = [(p[0], hexlify(p[1])) for p in _ap.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/api/access-point")
def request_access_point(request):
    data = request.GetPostedURLEncodedForm()
    print("Data", data)
    ssid = data.get("ssid", None)
    password = data.get("password", None)
    if not ssid or not password:
        request.Response.ReturnBadRequest()
        return

    print("SSID", ssid)
    print("Password", password)
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
