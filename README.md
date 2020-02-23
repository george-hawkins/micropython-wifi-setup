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
