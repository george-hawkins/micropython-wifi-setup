TODO:

Remove `print` calls in `main.py` or replace with logging calls.

Are you closing the DNS and slim-server server sockets?

Remove OptionsModule.

Update `../wifi-setup-material/screenshot.png`

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after portal has exited.

Maybe rename wifi-setup-material to material-wifi-setup - and grep for all old usages of wifi-setup-material, e.g. in `update-www`.

Document known issues:

* Insecure transmission and storage.
* Review code and .md files for other known issues.
