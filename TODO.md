TODO:

Remove `print` calls in `main.py` or replace with logging calls.

Make `lib/util.py` a less generic name or roll up into some other class.

Are you closing the DNS and slim-server server sockets?

Remove OptionsModule.

Test with UTF-8 access point names.

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after portal has exited.

Move `www` relative to classes that use it.

Maybe rename wifi-setup-material to material-wifi-setup - and grep for all old usages of wifi-setup-material, e.g. in `update-www`.

Document known issues:

* Insecure transmission and storage.
* Review code and .md files for other known issues.
