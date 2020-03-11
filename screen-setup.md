Screen and rshell
-----------------

Start screen:

    $ screen -q

Split the screen with `ctrl-A` and `S`.

Tab to the new area with `ctrl-A` and `tab`.

Start a shell here with `ctrl-A` and `c`.

Activate you venv and start `rshell`:

    $ source env/bin/activate
    $ rshell -p /dev/cp2104 --buffer-size 512 --quiet
    > repl

Tab back to the first area and use `curl`:

    $ curl -v 192.168.0.178/index.html

To scroll backwards within an area use `ctrl-A` and `ESC` - you enter a quasi-vi mode and can move around with your mouse scroll wheel or the usual vi movement keys.

To exit scroll mode (actually it's called _copy mode_) just press `ESC` again (actually any key which doesn't have a special _copy mode_ meaning will do).
