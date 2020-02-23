ESP32-Setup
===========

Basis setup:

    $ source ~/esp-env/bin/activate
    $ export PORT=/dev/cu.SLAB_USBtoUART

Copying files:

    $ pyboard.py --device $PORT -f cp main.py :

REPL:

    $ screen $PORT 115200

---

Currently `main.py` pulls in just MicroWebSrv2 and MicroDNSSrv.

slimDNS on its own is pulled in with `main-mdns.py` - to install it instead of `main.py`:

    $ pyboard.py --device $PORT -f cp main-mdns.py :main.py

To query the name advertised by `main-mdns.py`:

    $ dig -p 5353 portal.local @224.0.0.251

---

About 100 lines of `slimDNS.py` involves code to detect name clashes, e.g. if you use the name `alpha` it checks first to see if something else is already advertising this name.

I removed this code and in doing so I also removed `resolve_mdns_address`, i.e. the ability to resolve mDNS addresses - now the code can only advertise addresses.

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
    "Sonja’s iPhone",
    "664de20a139f",
    6
  ],
  ...
```
