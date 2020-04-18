TODO:

Maybe have a CheckpointModules class that can checkpoint `sys.modules` and retore a checkpoint (with a list of modules not to remove, e.g. the modules that are present when WiFiSetup does its job without needing the portal).

See <https://docs.micropython.org/en/latest/reference/constrained.html> - in particular `micropython.mem_info(1)`.

---

Put a README in `lib` so that even other projects simply copy it, there's a reference there to this project.

---

Document known issues:

* Insecure transmission and storage.
* I regret not having unit tests - as always it was a false economy not adding them from the start.
* Review code and .md files for other known issues.

---

Deleting all the modules gets you back most of your memory:

    for key in sys.modules:
        del sys.modules[key]

See <https://stackoverflow.com/a/487718/245602>

See which ones are really memory heavy. Maybe this and closing the server sockets will be enough.

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after portal has exited.
