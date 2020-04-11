MicroPython WiFi setup
======================

Basic setup:

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install --upgrade pip
    $ pip install rshell

Only the `source` step needs to be repeated, whenever you create a new terminal session.

On Mac:

    $ PORT=/dev/cu.SLAB_USBtoUART

On Linux:

    $ PORT=/dev/ttyUSB0

Or if you've setup a `udev` rule to create a fixed name:

    $ PORT=/dev/cp2104

Then to interact with the MicroPython board:

    $ rshell -p $PORT --buffer-size 512 --quiet

To clear the filesystem on the board:

    $ rshell -p $PORT --buffer-size 512 --quiet repl '~ import os ~ os.VfsFat.mkfs(bdev) ~'

Note: this will also remove `boot.py` - if you've got any special boot setup, you should copy this file and restore it after the clean-up.

To install this project:

    $ rshell -p $PORT --buffer-size 512 --quiet
    > cp -r main.py slim www /pyboard

Go into the REPL and reset the board, it'll complain that "WiFi credentials have not been configured":

    > repl
    ...
    Exception: WiFi credentials have not been configured

To set them:

    >>> db[SSID] = "My WiFi network"
    >>> db[PASSWORD] = "My WiFi password"
    >>> db.flush()
    0

Now reset the board again, this time it should confirm that it connected successfully to your WiFi network:

    Connected to b'My WiFi network' with address 192.168.0.178
     + [@WebRoute] GET /access-points (Access Points)
     + [@WebRoute] POST /authenticate (Authenticate)

Now it another terminal session you can test things out with `curl` and the address reported in the previous step:

    $ ADDR=192.168.0.178
    $ curl -v $ADDR

You'll see the request and response headers and [`www/index.html`](www/index.html) will be returned as the content.

There are more examples in [`request-examples.md`](request-examples.md).

Notes
-----

The web server code is derived from [MicroWebSrv2](https://github.com/jczic/MicroWebSrv2) authored by Jean-Christophe Bos at HC<sup>2</sup> and is licensed under the [MIT license](https://github.com/jczic/MicroWebSrv2/blob/master/LICENSE.md).

The DNS server code is derived from [MicroDNSSrv](https://github.com/jczic/MicroDNSSrv/), also authored by Jean-Christophe Bos and licensed under the MIT license.

The schedule code is derived from [schedule](https://github.com/rguillon/schedule) authored by Renaud Guillon and is licensed under the [MIT license](https://github.com/rguillon/schedule/blob/master/LICENSE.txt).

The logging package is [micropython-lib/logging](https://github.com/micropython/micropython-lib/blob/master/logging) authored by Paul Sokolovsky (aka Pfalcon) and is licensed under the [MIT license](https://github.com/micropython/micropython-lib/blob/master/logging/setup.py) (see `license` key).
