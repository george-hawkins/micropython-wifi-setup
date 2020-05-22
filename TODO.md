TODO
----

When you complete the setup process, you'll find that a lot of heap is no longer available even if you explicitly delete the setup object.

This is a bit disappointing as a lot of code changes were made to ensure there aren't random structures, e.g. file local maps, left lying around at the end of the process.

Deleting all the modules gets you back some of your memory:

    for key in sys.modules:
        del sys.modules[key]

See <https://stackoverflow.com/a/487718/245602>

However the order you delete them seems to make a big difference to how much memory you eventually recover.

Maybe have a CheckpointModules class that can checkpoint `sys.modules` and restore a checkpoint (with a list of modules not to remove, e.g. the modules that are present when WiFiSetup does its job without needing the portal).

See <https://docs.micropython.org/en/latest/reference/constrained.html> - in particular `micropython.mem_info(1)`.

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after the portal has exited.
