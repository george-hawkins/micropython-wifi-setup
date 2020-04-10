TODO:

Remove `print` calls in `main.py` or replace with logging calls.

Make `lib/util.py` a less generic name or roll up into some other class.

Remove OptionsModule.

Test with UTF-8 access point names.

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after portal has exited.

Maybe rename wifi-setup-material to material-wifi-setup - and grep for all old usages of wifi-setup-material, e.g. in `update-www`.

Document known issues:

* Insecure transmission and storage.
* Lock and signal strength icons are pretty for show (already noted in ../wifi-setup-material/NOTES.md).
* Review code and .md files for other known issues.

Update:

It seems I do now get SSID, BSSID, channel, RSSI, authmode and hidden:

    (b'George Hawkins AC', b'x\x8a I\x8c&', 1, -58, 3, False)
