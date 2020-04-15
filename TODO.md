TODO:

Put a README in `lib` so that even other projects simply copy it, there's a reference there to this project.

Are you closing the DNS and slim-server server sockets?

Deregister sockets from poller and close poller (if it has a close).

Deregister web routes.

Maybe have a global variable `singleton_portal` or simply get rid of decorators and make web_route more oo.

Document known issues:

* Insecure transmission and storage.
* I regret not having unit tests - as always it was a false economy not adding them from the start.
* Review code and .md files for other known issues.

Deleting all the modules gets you back most of your memory:

    for key in sys.modules:
        del sys.modules[key]

See <https://stackoverflow.com/a/487718/245602>

See which ones are really memory heavy. Maybe this and closing the server sockets will be enough.

Try using `globals()`, `locals()` and anything similar to find out what holds onto memory after portal has exited.
