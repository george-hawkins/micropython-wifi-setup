MicroPython WiFi setup
======================

Basic setup:

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install --upgrade pip
    $ pip install rshell

Only the `source` step needs to be repeated, whenever you create a new terminal session.

On Mac:

    $ export PORT=/dev/cu.SLAB_USBtoUART

On Linux:

    $ export PORT=/dev/ttyUSB0

Or if you've setup a `udev` rule to create a fixed name:

    $ export PORT=/dev/cp2104


Then to interact with the MicroPython board:

    $ rshell -p $PORT --buffer-size 512 --quiet

Notes
-----

The web server code is derived from [MicroWebSrv2](https://github.com/jczic/MicroWebSrv2) by Jean-Christophe Bos at HC<sup>2</sup> which is licensed under the [MIT license](https://github.com/jczic/MicroWebSrv2/blob/master/LICENSE.md).
