# The compiler needs a lot of space to process the server classes etc. so
# import them first before anything else starts to consume memory.
from slim.slim_server import SlimServer
from slim.slim_config import SlimConfig
from slim.fileserver_module import FileserverModule
from slim.web_route_module import WebRouteModule, RegisteredRoute, HttpMethod
from micro_dns_srv import MicroDNSSrv
from shim import join, dirname

import network
import select
import time
import logging

from schedule import Scheduler, CancelJob


_logger = logging.getLogger("captive_portal")


# Rather than present a login page, this is a captive portal that lets you set up
# access to your network. See docs/captive-portal.md for more about captive portals.
class CaptivePortal:
    def run(self, essid, connect, captive_timeout=None):
        self._schedule = Scheduler()
        self._connect = connect
        self._alive = True
        self._timeout_job = None
        self.captive_timeout = captive_timeout

        self._ap = network.WLAN(network.AP_IF)
        self._ap.active(True)
        self._ap.config(essid=essid)  # You can't set values before calling active(...).

        poller = select.poll()

        addr = self._ap.ifconfig()[0]
        slim_server = self._create_slim_server(poller, essid)
        dns = self._create_dns(poller, addr)

        _logger.info("captive portal web server and DNS started on %s", addr)

        # Used as reference for the Captive Portal timeout
        if self.captive_timeout:
            start = time.ticks_ms()

        # If no timeout is given `ipoll` blocks and the for-loop goes forever.
        # With a timeout the for-loop exits every time the timeout expires.
        # I.e. the underlying iterable reports that it has no more elements.
        while self._alive:
            if (
                self.captive_timeout
                and time.ticks_diff(time.ticks_ms(), start) > self.captive_timeout
            ):
                _logger.info("Captive portal timeout reached")
                return
            # Under the covers polling is done with a non-blocking ioctl call and the timeout
            # (or blocking forever) is implemented with a hard loop, so there's nothing to be
            # gained (e.g. reduced power consumption) by using a timeout greater than 0.
            for (s, event) in poller.ipoll(0):
                # If event has bits other than POLLIN or POLLOUT then print it.
                if event & ~(select.POLLIN | select.POLLOUT):
                    self._print_select_event(event)
                slim_server.pump(s, event)
                dns.pump(s, event)

            slim_server.pump_expire()  # Expire inactive client sockets.
            self._schedule.run_pending()

        slim_server.shutdown(poller)
        dns.shutdown(poller)

        self._ap.active(False)

    def _create_slim_server(self, poller, essid):
        # See the captive portal notes in docs/captive-portal.md for why we redirect not-found
        # URLs and why we redirect them to an absolute URL (rather than a path like "/").
        # `essid` is used as the target host but any name could be used, e.g. "wifi-setup".
        config = SlimConfig(not_found_url="http://{}/".format(essid))

        slim_server = SlimServer(poller, config=config)

        # fmt: off
        slim_server.add_module(WebRouteModule([
            RegisteredRoute(HttpMethod.GET, "/api/access-points", self._request_access_points),
            RegisteredRoute(HttpMethod.POST, "/api/access-point", self._request_access_point),
            RegisteredRoute(HttpMethod.POST, "/api/alive", self._request_alive)
        ]))
        # fmt: on

        root = self._get_relative("www")
        # fmt: off
        slim_server.add_module(FileserverModule({
            "html": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "woff2": "font/woff2",
            "ico": "image/x-icon",
            "svg": "image/svg+xml"
        }, root))
        # fmt: on

        return slim_server

    # Find a file, given a path relative to the directory contain this `.py` file.
    @staticmethod
    def _get_relative(filename):
        return join(dirname(__file__), filename)

    @staticmethod
    def _create_dns(poller, addr):
        addr_bytes = MicroDNSSrv.ipV4StrToBytes(addr)

        def resolve(name):
            _logger.info("resolving %s", name)
            return addr_bytes

        return MicroDNSSrv(resolve, poller)

    def _request_access_points(self, request):
        # Tuples are  of the form (SSID, BSSID, channel, RSSI, authmode, hidden).
        points = [(p[0], p[3], p[4]) for p in self._ap.scan()]
        request.Response.ReturnOkJSON(points)

    def _request_access_point(self, request):
        data = request.GetPostedURLEncodedForm()
        _logger.debug("connect request data %s", data)
        ssid = data.get("ssid", None)
        if not ssid:
            request.Response.ReturnBadRequest()
            return

        password = data.get("password", None)

        result = self._connect(ssid, password)
        if not result:
            request.Response.ReturnForbidden()
        else:
            request.Response.ReturnOkJSON({"message": result})

    def _request_alive(self, request):
        data = request.GetPostedURLEncodedForm()
        timeout = data.get("timeout", None)
        if not timeout:
            request.Response.ReturnBadRequest()
            return

        _logger.debug("timeout %s", timeout)
        timeout = int(timeout) + self._TOLERANCE
        if self._timeout_job:
            self._schedule.cancel_job(self._timeout_job)
        self._timeout_job = self._schedule.every(timeout).seconds.do(self._timed_out)

        request.Response.Return(self._NO_CONTENT)

    # If a client specifies a keep-alive period of Xs then they must ping again within Xs plus a fixed "tolerance".
    _TOLERANCE = 1
    _NO_CONTENT = 204

    def _timed_out(self):
        _logger.info("keep-alive timeout expired.")
        self._alive = False
        self._timeout_job = None
        return CancelJob  # Tell scheduler that we want one-shot behavior.

    _POLL_EVENTS = {
        select.POLLIN: "IN",
        select.POLLOUT: "OUT",
        select.POLLHUP: "HUP",
        select.POLLERR: "ERR",
    }

    def _print_select_event(self, event):
        mask = 1
        while event:
            if event & 1:
                _logger.info("event %s", self._POLL_EVENTS.get(mask, mask))
            event >>= 1
            mask <<= 1
