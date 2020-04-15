# The compiler needs a lot of space to process the server classes etc. so
# import them first before anything else starts to consume memory.
from micro_dns_srv import MicroDNSSrv
from slim.fileserver_module import FileserverModule
from slim.slim_config import SlimConfig
from slim.slim_server import SlimServer
from slim.web_route_module import WebRouteModule
from micro_web_srv_2.web_route import WebRoute, HttpMethod

import network
import select
import logging

from schedule import Scheduler, CancelJob


_logger = logging.getLogger("captive_portal")

_ap = network.WLAN(network.AP_IF)

_schedule = Scheduler()

_connect = None
_alive = True


# Find a file, given a path relative to the directory contain this `.py` file.
def _get_relative(filename):
    from shim import join, dirname

    return join(dirname(__file__), filename)


# Rather than present a login page, this is a captive portal that lets you setup
# access to your network. See docs/NOTES.md for more about captive portals.
def portal(essid, connect):
    global _connect
    _connect = connect
    _ap.active(True)
    _ap.config(essid=essid)  # You can't set values before calling active.

    poller = select.poll()

    # See the captive portal notes in docs/NOTES.md for why we redirect not-found URLs
    # and why we redirect them to an absolute URL (rather than a path like "/").
    # `essid` is used as the target host but any name could be used, e.g. "wifi-setup".
    config = SlimConfig(not_found_url="http://{}/".format(essid))

    slim_server = SlimServer(poller, config=config)

    slim_server.add_module("webroute", WebRouteModule())

    root = _get_relative("www")
    # fmt: off
    slim_server.add_module("fileserver", FileserverModule({
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
        "woff2": "font/woff2",
        "ico": "image/x-icon",
        "svg": "image/svg+xml"
    }, root))
    # fmt: on

    addr = _ap.ifconfig()[0]
    addrBytes = MicroDNSSrv.ipV4StrToBytes(addr)

    def resolve(name):
        _logger.info("resolving %s", name)
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
                _print_select_event(event)
            slim_server.pump(s, event)
            dns.pump(s, event)

        slim_server.pump_expire()  # Expire inactive client sockets.
        _schedule.run_pending()

    _ap.active(False)


_POLL_EVENTS = {
    select.POLLIN: "IN",
    select.POLLOUT: "OUT",
    select.POLLHUP: "HUP",
    select.POLLERR: "ERR",
}


def _print_select_event(event):
    mask = 1
    while event:
        if event & 1:
            _logger.info("event %s", _POLL_EVENTS.get(mask, mask))
        event >>= 1
        mask <<= 1


@WebRoute(HttpMethod.GET, "/api/access-points")
def request_access_points(request):
    # Tuples are  of the form (SSID, BSSID, channel, RSSI, authmode, hidden).
    points = [(p[0], p[3], p[4]) for p in _ap.scan()]
    request.Response.ReturnOkJSON(points)


@WebRoute(HttpMethod.POST, "/api/access-point")
def request_access_point(request):
    data = request.GetPostedURLEncodedForm()
    _logger.debug("connect request data %s", data)
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
    _logger.info("keep-alive timeout expired.")
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

    _logger.debug("timeout %s", timeout)
    timeout = int(timeout) + _TOLERANCE
    global timeout_job
    if timeout_job:
        _schedule.cancel_job(timeout_job)
    timeout_job = _schedule.every(timeout).seconds.do(timed_out)

    request.Response.Return(_NO_CONTENT)
