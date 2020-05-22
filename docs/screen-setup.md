Screen and rshell
-----------------

I found it useful to use [`screen`](https://www.gnu.org/software/screen/) during development. Here are some basic usage notes.

Start `screen`:

    $ screen -q

Split the `screen` with `ctrl-A` and `S`.

Tab to the new area with `ctrl-A` and `tab`.

Start a shell here with `ctrl-A` and `c`.

Activate you venv and start `rshell`:

    $ source env/bin/activate
    $ PORT=/dev/ttyUSB0
    $ rshell --buffer-size 512 --quiet -p $PORT
    > repl

Tab back to the first area and use `curl`:

    $ ADDR=192.168.0.178
    $ curl -v $ADDR/index.html

To scroll backwards within an area use `ctrl-A` and `ESC` - you enter a quasi-vi mode and can move around with your mouse scroll wheel or the usual vi movement keys.

To exit scroll mode (actually it's called _copy mode_) just press `ESC` again (actually any key which doesn't have a special _copy mode_ meaning will do).

The above `screen` commands all work the same on Mac and Linux however, in some cases they're different. E.g. quit is `ctrl-A` and `\` on Linux, while on Mac it's `ctrl-A` and `ctrl-\`.
