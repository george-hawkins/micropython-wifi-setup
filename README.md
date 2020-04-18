MicroPython WiFi setup
======================

![screenshot](docs/images/screenshot.png)

The system works like this:

* Configure your device with a unique ID, to use as its access point name, and label the device with the ID.
* On startup the WiFi setup process checks if it already has credentials for a WiFi network and if so tries to connect to that.
* If it does not have existing credentials or cannot connect, it creates a temporary access point.
* The user looks at the label on the device and selects that access point on their phone.
* The access point is open but behaves like a [captive portal](https://en.wikipedia.org/wiki/Captive_portal), the phone detects this and prompts the user to go to a login webpage.
* Unlike the kind of login pages used by public WiFi services, this one presents the user with a list of WiFi networks that the device can see.
* The user selects the WiFi network to which they want to connect the device and they are then prompted for the password for that network.
* Once the device has successfully connected to the network, the user is presented with the device's new IP address.
* Then the temporary access point shuts down and the standard behavior for the phone is to automatically return to the previous network.
* The user can now use the IP address they now have to access the device.
* The device stores the network credentials and will use them to reconnect whenever the device is restarted.

Note: the setup process takes a callback that can perform additional steps on connecting to the network and can return something other than an IP address, e.g. an MQTT topic name.

For a quick **video** of the setup process in action, click [here](https://george-hawkins.github.io/micropython-wifi-setup/).

---

![device](docs/images/labeled-device.jpg)

It just requires two lines of code:

```python
ws = WiFiSetup("ding-5cd80b3")
sta = ws.connect_or_setup()
```

Or you can take a more fine grained approach:

```python
ws = WiFiSetup("ding-5cd80b3")
if ws.has_ssid():
    sta = ws.connect()
if not sta:
    sta = ws.setup()
```

You could e.g. make calling `setup()` conditional on a button being held down during startup.

If you want to you can clear any existing credentials with the static method `WiFiSetup.clear()`.

Note that the intention is that `WiFiSetup` is just used at startup - it's not as if it's working away continuously and your device will randomly enter setup mode whenever your WiFi becomes unavailable.

---

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

Licenses
--------

The code developed for this project is licensed under the [MIT license](LICENSE).

The web server code is derived from [MicroWebSrv2](https://github.com/jczic/MicroWebSrv2), authored by Jean-Christophe Bos at HC<sup>2</sup> and licensed under the [MIT license](https://github.com/jczic/MicroWebSrv2/blob/master/LICENSE.md).

The DNS server code is derived from [MicroDNSSrv](https://github.com/jczic/MicroDNSSrv/), also authored by Jean-Christophe Bos and licensed under the MIT license.

The schedule code is derived from [schedule](https://github.com/rguillon/schedule), authored by Renaud Guillon and licensed under the [MIT license](https://github.com/rguillon/schedule/blob/master/LICENSE.txt).

The logging package is [micropython-lib/logging](https://github.com/micropython/micropython-lib/blob/master/logging), authored by Paul Sokolovsky (aka Pfalcon) and licensed under the [MIT license](https://github.com/micropython/micropython-lib/blob/master/logging/setup.py) (see `license` key).
