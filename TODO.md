TODO:

Add schedule - pump via ipoll:

https://schedule.readthedocs.io/en/stable/faq.html#how-can-i-run-a-job-only-once
https://github.com/rguillon/schedule

Consider switching to micropython-logger (schedule uses it).

And then add `logger.debug("connection from {}:{} expired".format(self._cliAddr[0], self._cliAddr[1]))` to `XAsyncSocket.pump_expire`.

And add `logger.warn("no MIME type for {}".format(filename))` to `else` path if `if ct` in `FileserverModule`.

And remove my Logger class.

Show shutdown spinner until first GET access-points result (irrespective of 0 rows or failure) maybe rename the `alive` variable that controls this to `waiting` (although `alive` is kind of OK - maybe just change the `#shutdown` in the HTML to `#waiting` or `#spinning`).

Move things into `lib` with `slim`, `micro_srv_2`, `logging`, `shim.py` and `schedule` at top level.

Is there a standard Angular way to not make a request if the last such request hasn't completed yet?
See use of `fetching` in `getAccessPoints` in https://github.com/george-hawkins/wifi-setup-material/blob/master/src/app/access-points/access-points.component.ts
