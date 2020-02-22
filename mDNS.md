Support for mDNS was added for ESP32 in [MicroPython #4912](https://github.com/micropython/micropython/issues/4912).

Looking at the merged code, it looks like the hostname is taken from the station hostname.

I tried setting the hostname for both station and access point like so:

    ap = network.WLAN(network.AP_IF)
    sta = network.WLAN(network.STA_IF) # create station interface

    ap.active(True)
    sta.active(True)

    done = False
    while not done:
        try:
            ap.config(dhcp_hostname="ap.local")
            sta.config(dhcp_hostname="sta.local")
            print("hostnames set")
            done = True
        except:
            print(".")

But when connected to the ESP32, when functioning as an access point, I got nothing back for the following::

    $ dig -p 5353 my-hostname @224.0.0.251

I tried 'ap', 'sta', 'ap.local' and 'sta.local' without success.

---

A number of MicroPython variants have more substantial mDNS support:

* https://github.com/loboris/MicroPython_ESP32_psRAM_LoBo/wiki/mdns
* https://github.com/pycom/pycom-micropython-sigfox/pull/377 (there's no associated documentation)

---

Currently the best option seems to be the pure Python implementation [slimDNS](https://github.com/nickovs/slimDNS).
