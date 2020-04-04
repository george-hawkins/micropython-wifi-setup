ESP32-Setup
===========

Basic setup:

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install --upgrade pip
    $ curl -O https://raw.githubusercontent.com/micropython/micropython/master/tools/pyboard.py
    $ chmod a+x pyboard.py
    $ mv pyboard.py env/bin
    $ pip install pyserial

All these steps, except the `source`, just need to be done once. The `source` line needs to be executed whenever you create a new terminal session.

On Mac:

    $ export PORT=/dev/cu.SLAB_USBtoUART

On Linux:

    $ export PORT=/dev/ttyUSB0

Or if you've setup a `udev` rule to create a fixed name:

    $ export PORT=/dev/cp2104

Copying files:

    $ pyboard.py --device $PORT -f cp main.py :

REPL:

    $ screen $PORT 115200

---

Ideally you'd encrypt your WLAN password with an AES key printed on the device.

This would mean only that particular device, with the key pre-installed, could decrypt your password. It would also mean that only the person who's got the devise and can read the printed key can take constrol of it, i.e. register it with their WLAN.

However an AES key is at minimum 128 bits, i.e. 32 hex digits, which is more than most people would want to type in - and you'd probably want to include two checksum digits so that it's possible to point out if the key looks good or not.

One possibility would be to use a [password-based key derivation function](https://en.wikipedia.org/wiki/Key_derivation_function) (PBKDF) to generate a key from a more reasonable length password (see step 5. and the text below in this Crypto StackExchange [answer](https://crypto.stackexchange.com/a/53554/8854)). Currently [Argon2](https://en.wikipedia.org/wiki/Argon2) seems to be the first-choice PBKDF, however according to this [answer](https://forum.micropython.org/viewtopic.php?p=36116#p36116) on the MicroPython forums all such algorithms consume noticeable amounts of ROM "unlikely to ever appear by default in micropython firmware".

---

To pull in the new minimal `webserver.py`:

    $ pyboard.py --device $PORT -f cp webserver.py :main.py

---

Currently `main.py` pulls in just MicroWebSrv2 and MicroDNSSrv.

slimDNS on its own is pulled in with `main-mdns.py` - to install it instead of `main.py`:

    $ pyboard.py --device $PORT -f cp main-mdns.py :main.py

To query the names advertised by `main-mdns.py`:

    $ dig @224.0.0.251 -p 5353 portal.local
    $ dig @224.0.0.251 -p 5353 dns.local

To see all the queries that slimDNS sees, i.e. not just the ones relating to names that it's advertising, uncomment the `print` in `compare_packed_names`.

My Mac automatically tried to query for all these names:

```
_airplay
_airport
_apple-mobdev
_apple-pairable
_companion-link
_googlecast
_ipp
_ipps
_ippusb
_pdl-datastream
_printer
_ptp
_raop
_rdlink
_scanner
_sleep-proxy
_uscan
_uscans
```

---

Using slimDNS to lookup `dns.local` and then MicroDNSSrv to respond to any arbitrary name:

    $ dig +short @dns.local foobar

If you've overriden your nameserver to something like [8.8.8.8](https://en.wikipedia.org/wiki/Google_Public_DNS) then this is quite slow (I suspect it first tries to resolve `dns.local` via DNS and only then falls back to trying mDNS). In such a situation it's noticeably faster to explicitly resolve `dns.local` via mDNS:

    $ nameserver=$(dig +short @224.0.0.251 -p 5353 dns.local)
    $ dig +short @$nameserver foobar

If you haven't overriden your nameserver, i.e. just accept the one configured when you connect to an AP, then the `@nameserver` can be omitted altogether:

    $ dig +short foobar

---

About 100 lines of `slimDNS.py` involves code to detect name clashes, e.g. if you use the name `alpha` it checks first to see if something else is already advertising this name.

I removed this code and in doing so I also removed `resolve_mdns_address`, i.e. the ability to resolve mDNS addresses - now the code can only advertise addresses.

---

Look at what affect using [mpy-cross](https://github.com/micropython/micropython/tree/master/mpy-cross) has on available memory.

You can check available memory like so:

    >>> import micropython
    >>> micropython.mem_info()
    ...
    >>> import gc
    >>> gc.collect()
    >>> micropython.mem_info()
    ...

Maybe it makes no difference _once things are compiled_ but simply ensures that the compiler won't run out of memory doing its job?

---

Sources:

* https://github.com/jczic/MicroWebSrv2
* https://github.com/nickovs/slimDNS/blob/638c461/slimDNS.py
* https://github.com/jczic/MicroDNSSrv/blob/ebe69ff/microDNSSrv.py

---

Note `LICENSE.md` is from MicroDNSSrv rather than being a license actively chosen by me.

---

You can dump the visible access points like so:

    >>> json.dumps([(t[0], binascii.hexlify(t[1]), t[2]) for t in sta.scan()])

When using the REPL, it escapes single quotes, i.e. "Foo's AP" is displayed as "Foo\'s AP", which is invalid JSON. This is just a REPL artifact. To get the un-munged JSOM:

    >>> import network
    >>> import json
    >>> import binascii
    >>> sta = network.WLAN(network.STA_IF)
    >>> sta.active(True)
    >>> with open('data.json', 'w') as f:
    >>>     json.dump([(t[0], binascii.hexlify(t[1]), t[2]) for t in sta.scan()], f)

    $ pyboard.py --device $PORT -f cp :data.json data.json

The results (prettified) are something like this:

```json
[
  [
    "UPC Wi-Free",
    "3a431d3e4ec7",
    1
  ],
  [
    "Salt_2GHz_8A9F85",
    "44fe3b8a9f87",
    11
  ],
  [
    "JB_40",
    "488d36d5c83a",
    11
  ],
  [
    "Sonja's iPhone",
    "664de20a139f",
    6
  ],
  ...
```

---

There are various interesting ports of MicroPython, some of which contain, among other things, e.g. more extensive support for ESP32 features.

See Adafruit's page on the "[many forks & ports of MicroPython](https://github.com/adafruit/awesome-micropythons)".

---

If you're posting data using `curl` you won't see the data even with `-v` as it doesn't show the body content that's sent:

    $ curl -v --data 'bssid=alpha&password=beta' 192.168.0.178/authenticate

If you want to see the headers _and_ body content, you have to replace `-v` with `--trace-ascii -` like so:

    $ curl --trace-ascii - --data 'bssid=alpha&password=beta' 192.168.0.178/authenticate

---

In CPython objects have an associated `__dict__`. In MicroPython 1.12 this isn't available, but if you e.g. want to lookup the name of a constant value you can do:

    def name(obj, value):
        for a in dir(obj):
            if getattr(obj, a) == value:
                return a
        return value

    name(network, 201)

Note that this code assumes that all attributes will have unique values, e.g. here that `network` only has one constant with value 201.

It's probably better to filter for the names that you want:

    names = [s for s in dir(network) if s.startswith("STAT_")]
    stats = { getattr(network, k) : k for k in names }

---

MicroPython `sys.print_exception(e)` is equivalent to CPython `traceback.print_exception(e.__class__, e, e.__traceback__)`.

---

I set the project to use the python interpreter from my venv - Settings / Project:my-project-name / Project Interpreter - clicked cog and select _Add_, it automatically selected _Existing environment_ and the interpreter in my venv - so I just had to press OK.

---

PyCharm MicroPython plugin
--------------------------

Setup:

* Settings / Plugins - added MicroPython plugin.
* Settings / Languages & Frameworks - ticked _Enable MicroPython support_, set device as ESP8266 (ESP32 isn't an option) and manually set _Device path_ (as _Detect_ didn't work) to `/devcp2104`.

However this doesn't get you very far - for autocompletion and knowing what methods are available it depends on https://github.com/vlasovskikh/intellij-micropython/tree/master/typehints

The type hints haven't been updated in 2 years and were never very extensive, e.g. the only `stdlib` module it has hints for is `utime`.

So it doesn't know about `sys.print_exception` and other MicroPython specific functions.

Note: `vlasovskikh` is Andrey Vlasovskikh - he is the technical lead on PyCharm.

In the end, I uninstalled the plugin - the other features it offered seemed little more convenient than using `rshell`.

Black and Flake8
----------------

The code is formatted with [Black](https://black.readthedocs.io/en/stable/) and checked with [Flake8](https://flake8.pycqa.org/en/latest/).

    $ pip install black
    $ pip install flake8

To reformat, provide a list of files and/or directories to `black`:

    $ black ...

To check, provide a list of files and/or directories to `flake8`:

    $ flake8 ... | fgrep -v -e E501 -e E203 -e E722

Here `fgrep` is used to ignore E501 (line too long) and E203 (whitespace before ':') as these are rules that Black and Flake8 disagree on. I also ignore E203 (do not use bare 'except') as I'm not prepared to enforce this rule in the code.
