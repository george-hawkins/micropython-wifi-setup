MicroPython WiFi setup
======================

![screenshot](docs/images/screenshot.png)

For a quick walkthru of the following steps, with screenshots, click [here](docs/steps.md). For a quick video of the setup process in action, click [here](https://george-hawkins.github.io/micropython-wifi-setup/).

The system works like this:

* Configure your device with a unique ID, to use as its access point name, and physically label the device with the ID.
* On startup the WiFi setup process checks if it already has credentials for a WiFi network and if so tries to connect to that.
* If it does not have existing credentials or cannot connect, it creates a temporary access point.
* The user looks at the label on the device and selects that access point on their phone.
* The access point is open but behaves like a [captive portal](https://en.wikipedia.org/wiki/Captive_portal), the phone detects this and prompts the user to go to a login webpage.
* Unlike the kind of login pages used by public WiFi services, this one presents the user with a list of WiFi networks that the device can see.
* The user selects the WiFi network to which they want to connect the device and are then prompted for the password for that network.
* Once the device has successfully connected to the network, the user is presented with the device's new IP address.
* Then the temporary access point shuts down (and the standard behavior for the phone is to automatically return to the previous network).
* The user can now use the IP address they have to access the device.
* The device stores the network credentials and will use them to reconnect whenever the device is restarted.

Note: the setup process takes a callback that can perform additional steps on connecting to the network and can return something other than an IP address, e.g. an MQTT topic name.

Using this library
------------------

![device](docs/images/labeled-device.jpg)

Each device should be given a unique name. Then you just need to add two lines of code at the start of your `main.py` file:

```python
ws = WiFiSetup("ding-5cd80b1")
sta = ws.connect_or_setup()
```

Above, I've specified `"ding-5cd80b1"` as the device unique name (which it will use as the name of the temporary access point that it creates). And calling `ws.connect_or_setup()` will go through the steps outlined up above. Once complete the resulting [`network.WLAN`](https://docs.micropython.org/en/latest/library/network.WLAN.html), corresponding to the connected network, will be assigned to `sta`.

Or you can take a more fine grained approach:

```python
ws = WiFiSetup("ding-5cd80b1")
sta = None
if ws.has_ssid():
    sta = ws.connect()
if not sta:
    sta = ws.setup()
```

Here `ws.has_ssid()` checks if credentials for an SSID already exist, if so just connect with `ws.connect()` (if this fails it returns `None`). If there are no existing credentials or `ws.connect()` fails then call `ws.setup()` to create a temporary access point so that the user can go through the steps up above.

If you don't want your board to automatically going into setup mode, you could e.g. make calling `ws.setup()` conditional on a button being held down during startup.

If you want to you can clear any existing credentials with the static method `WiFiSetup.clear()`.

Note that the intention is that `WiFiSetup` is just used at startup - it's **not** working away continuously and your device will **not** randomly enter setup mode whenever your WiFi becomes unavailable.

Basic setup
-----------

If you haven't already got Python 3 installed on your local system, see my [notes](https://github.com/george-hawkins/snippets/blob/master/install-python.md) on installing it.

And if you're new to MicroPython, see my [notes](https://github.com/george-hawkins/micropython-notes/blob/master/getting-started.md) on getting it installed on your development board.

This library has been tested with the stable version of MicroPython 1.12 for both ESP-IDF 3.x and 4.x on boards with both WROOM and WROVER modules.

To get started, first checkout this project:

    $ git clone git@github.com:george-hawkins/micropython-wifi-setup.git
    $ cd micropython-wifi-setup

Then create a Python venv and install [`rshell`](https://github.com/dhylands/rshell):

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install --upgrade pip
    $ pip install rshell

Only the `source` step needs to be repeated (whenever you open a new terminal session). For more about `rshell`, see my notes [here](https://github.com/george-hawkins/micropython-notes/blob/master/tools-filesystem-and-repl.md#rshell).

All the snippets below assume you've set the variable `PORT` to point to the serial device corresponding to your board.

On Mac you typically just need to do:

    $ PORT=/dev/cu.SLAB_USBtoUART

And on Linux, it's typically:

    $ PORT=/dev/ttyUSB0

Then start `rshell` to interact with the MicroPython board:

    $ rshell --buffer-size 512 --quiet -p $PORT
    >

Within `rshell` just copy over the library like so to your board:

    > cp -r lib /pyboard

The `lib` directory contains a substantial amount of code so copying it across takes about 130 seconds. A progress meter would be nice but as it is `rshell` sits there silently until copying is complete.

Then to copy over a demo `main.py` and some supporting files:

    > cd demo
    > cp -r main.py www /pyboard

The demo just includes the Python code outlined up above followed by a simple webserver that can be accessed, once the board is connected to a network, in order to demonstrate that the whole process worked.

Then enter the REPL and press the reset button on the board (the `EN` button if you're using an Espressif ESP32 DevKitC board):

    > repl
    ...
    INFO:captive_portal:captive portal web server and DNS started on 192.168.4.1

You'll see a lot of boot related line scroll by and finally you should see it announce that it's started a captive portal. Then just go to your phone and walk through the phone related steps that are shown with screenshot [here](docs/steps.md). Once connected to your network your board will serve a single web page (of a cute little ghost).

If you reset the board it will now always connect to the network you just configured via your phone. If you want to clear the stored credentials just do:

    > repl
    >>> WiFiSetup.clear()

PyPI and this library
---------------------

I did initially try to make this library available via [PyPI](https://pypi.org/) so that it could be installed using [`upip`](https://docs.micropython.org/en/latest/reference/packages.html#upip-package-manager). This took much longer than it should have due to my insistence on trying to get the process to work using [Python Poetry](https://python-poetry.org/) (see my notes [here](docs/python-poetry.md)). But in the end the effort was all rather pointless as `upip` has not worked for quite some time on the ESP32 port of MicroPython (due to TLS related issues, see issue [#5543](https://github.com/micropython/micropython/issues/5543)).

Anyway, there something fundamentally odd about installing a library that's meant to setup a WiFi connection using a tool, i.e. `upip`, that requires that your board already has a WiFi connection.

Given that, issue #5543 and Thorsten von Eicken's [comment](https://github.com/micropython/micropython/issues/5543#issuecomment-621341369) that "I have the feeling that long term MP users don't use upip" (I did not use `upip` at any point when creating this project), I decided to give up on publishing this library to PyPI.

Using micropython-wifi-setup in your own project
------------------------------------------------

Let's say you have a project called `my-project`, then I suggest the following approach to using the micropython-wifi-setup library within this project:

    $ ls
    my-project  ...
    $ git clone git@github.com:george-hawkins/micropython-wifi-setup.git
    $ LIB=$PWD/micropython-wifi-setup/lib
    $ cd my-project
    $ ln -s $LIB .
    $ echo lib/ >> .gitignore

You could of course just copy the micropython-wifi-setup `lib` directory into your own project but this means your copy is frozen in time. The approach just outlined means that's it's easy to keep up-to-date with changes and it makes it easier to contribute back any improvements you make to the original project, to the benefit of a wider audience.

Web resources
-------------

The web related resources found in [`lib/wifi_setup/www`](lib/wifi_setup/www) were created in another project - [material-wifi-setup](https://github.com/george-hawkins/material-wifi-setup).

If you check out that project in the same parent directory as this project and then make changes there, you can rebuild the resources and copy them here like so:

    $ ./update-lib-www

The script `update-lib-www` does some basic sanity checking and ensures that it doesn't stomp on any changes made locally in this project. Note that it compresses some of the resources when copying them here.

### Supported browsers

The provided web interface should work for any version of Chrome, Firefox, Edge or Safari released in the last few years. It may not work for older tablets or phones that have gone out of support and are no longer receiving updates. It is possible to support older browsers but this means significantly increasing the size of the web resource included here - for more details see the "supported browser versions" section [here](https://github.com/george-hawkins/material-wifi-setup#supported-browser-versions).

Captive portals
---------------

This library uses what's termed a captive portal - this depends on being able to respond to all DNS requests. This works fine on phones - it's the same process that's used whenever you connect to public WiFi at a coffee shop or an airport. However, on a laptop or desktop things may be different. If you've explicitly set your nameserver to something like Google's [public DNS](https://en.wikipedia.org/wiki/Google_Public_DNS) then your computer may never try resolving addresses via the DNS server that's part of this library. In this case, once connected to the temporary access point, you have to explicitly navigate to the IP address we saw in the logging output above, i.e.:

    INFO:captive_portal:captive portal web server and DNS started on 192.168.4.1

A more sophisticated setup would sniff all packets and spot DNS requests, even to external but unreachable services like 8.8.8.8, and spoof a response - however this requires [promiscuous mode](https://en.wikipedia.org/wiki/Promiscuous_mode) which isn't currently supported in MicroPython.

For more about captive portals see the captive portal notes in [`docs/captive-portal.md`](docs/captive-portal.md).

Reusable parts
--------------

There's a substantial amount of code behind the WiFi setup process. Some of the pieces may be useful in your own project.

How to reuse the web server:

```python
poller = select.poll()

slim_server = SlimServer(poller)
slim_server.add_module(FileserverModule({ "html": "text/html" }))

while True:
    for (s, event) in poller.ipoll(0):
        slim_server.pump(s, event)
    slim_server.pump_expire()
```

Create a `www` directory and add an `index.html` there. For every different file suffix used, you have to add a suffix-to-[MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types) mapping. In the snippet above the only mapping provided is from the suffix `html` to MIME type `text/html`.

Notes
-----

See [`docs/NOTES.md`](docs/NOTES.md) for more implementation details.

Licenses and credits
--------------------

The code developed for this project is licensed under the [MIT license](LICENSE).

The web server code is derived from [MicroWebSrv2](https://github.com/jczic/MicroWebSrv2), authored by Jean-Christophe Bos at HC<sup>2</sup> and licensed under the [MIT license](https://github.com/jczic/MicroWebSrv2/blob/master/LICENSE.md).

The DNS server code is derived from [MicroDNSSrv](https://github.com/jczic/MicroDNSSrv/), also authored by Jean-Christophe Bos and licensed under the MIT license.

The schedule code is derived from [schedule](https://github.com/rguillon/schedule), authored by Renaud Guillon and licensed under the [MIT license](https://github.com/rguillon/schedule/blob/master/LICENSE.txt).

The logging package is [micropython-lib/logging](https://github.com/micropython/micropython-lib/blob/master/logging), authored by Paul Sokolovsky (aka Pfalcon) and licensed under the [MIT license](https://github.com/micropython/micropython-lib/blob/master/logging/setup.py) (see `license` key).
