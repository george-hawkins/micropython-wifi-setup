Notes
=====

This page contains miscellaneous notes that were accumulated in the process of creating this project.

There are also some additional notes, separated out into [`screen-setup.md`](screen-setup.md) (basic usage notes for `screen`) and [`request-examples.md`](request-examples.md) (notes on using `curl` during development).

Connection failure reason
-------------------------

It's not currently possible to report why connecting to an access point fails, e.g. an invalid password.

For more details, see my MicroPython [forum post](https://forum.micropython.org/viewtopic.php?t=7942) about how `WLAN.status()` currently works.

WiFi password encryption
------------------------

Ideally, you'd encrypt your WiFi password with an AES key printed on the device.

This would mean only that particular device, with the key pre-installed, could decrypt your password. It would also mean that only the person who's got the device and can read the printed key can take control of it, i.e. register it with their WiFi.

However an AES key is at minimum 128 bits, i.e. 32 hex digits, which is more than most people would want to type in - and you'd probably want to include two checksum digits so that it's possible to point out if the key looks good or not.

One possibility would be to use a [password-based key derivation function](https://en.wikipedia.org/wiki/Key_derivation_function) (PBKDF) to generate a key from a more reasonable length password (see step 5. and the text below it in this Crypto StackExchange [answer](https://crypto.stackexchange.com/a/53554/8854)). Currently, [Argon2](https://en.wikipedia.org/wiki/Argon2) seems to be the first-choice PBKDF, however, according to this [answer](https://forum.micropython.org/viewtopic.php?p=36116#p36116) on the MicroPython forums all such algorithms consume noticeable amounts of ROM, making them "unlikely to ever appear by default in micropython firmware".

Testing connection timeout logic
--------------------------------

To test the timeout logic that expires sockets, replace `$ADDR` with the address of your device and try:

    $ telnet $ADDR 80

Just leave it there or paste in e.g. just the first line of a request:

    GET / HTTP/1.1

Within a few seconds (the time configured via `SlimConfig.timeout_sec`) the server will drop the connection.

MicroPython UNIX port
---------------------

Installing the UNIX port of MicroPython on your local system is very convenient using `pyenv`. Normally, you only mark one version of Python as active using `pyenv`. It is possible though to make both your normal CPython version and MicroPython available at the same time.

First, determine the currently active version of Python:


    $ pyenv global
    3.6.9
    $ python --version
    Python 3.6.9

Then install MicroPython and make both it and your current Python version available:

    $ pyenv update
    $ pyenv install micropython-1.12
    $ pyenv global 3.6.9 micropython-1.12

Check that you can access both:

    $ python --version
    Python 3.6.9
    $ micropython 
    MicroPython v1.12 on 2020-04-26; linux version
    ...

Due to PR [#1587](https://github.com/pyenv/pyenv/pull/1587), you should make sure your `pyenv` is up-to-date - hence the use of `pyenv update` above.

On macOS, you _may_ have to set `PKG_CONFIG_PATH` and `LDFLAGS` as shown in `pyenv` issue [#1588](https://github.com/pyenv/pyenv/issues/1588) before installing MicroPython.

REPL munges JSON
----------------

Using the MicroPython REPL, you can dump the visible access points like so:

    >>> json.dumps([(t[0], binascii.hexlify(t[1]), t[2], t[3], t[4], t[5]) for t in sta.scan()])

However the REPL escapes single quotes, i.e. "Foo's AP" is displayed as "Foo\\'s AP", which is invalid JSON. This is just a REPL artifact. To get the un-munged JSON:

    >>> import network
    >>> import json
    >>> import binascii
    >>> sta = network.WLAN(network.STA_IF)
    >>> sta.active(True)
    >>> with open('data.json', 'w') as f:
    >>>     json.dump([(t[0], binascii.hexlify(t[1]), t[2], t[3], t[4], t[5]) for t in sta.scan()], f)

    $ rshell --buffer-size 512 --quiet -p $PORT cp /pyboard/data.json .

The results (prettified) are something like this:

```json
[
  [
    "Foo's AP",
    "44fe3b8a9f87",
    11,
    -82,
    3,
    false
  ],
  [
    "UPC Wi-Free",
    "3a431d3e4ec7",
    11,
    -56,
    5,
    false
  ]
]
```

Try mpy-cross
-------------

Look at what affect using [mpy-cross](https://github.com/george-hawkins/micropython-notes/blob/master/precompiling.md) has on available memory.

You can check available memory like so:

    >>> import micropython
    >>> micropython.mem_info()
    ...
    >>> import gc
    >>> gc.collect()
    >>> micropython.mem_info()
    ...

Maybe it makes no difference _once things are compiled_ and simply ensures that the compiler won't run out of memory doing its job.

PyCharm Python version
----------------------

If you've created your venv before you open the project in PyCharm then it will automatically pick up the Python version from the venv. Otherwise, go to _Settings / Project:my-project-name / Project Interpreter_ - click the cog and select _Add_, it should automatically select _Existing environment_ and the interpreter in the venv - you just have to press OK.

Black and Flake8
----------------

The code here is formatted with [Black](https://black.readthedocs.io/en/stable/) and checked with [Flake8](https://flake8.pycqa.org/en/latest/).

    $ pip install black
    $ pip install flake8

To reformat, provide a list of files and/or directories to `black`:

    $ black ...

To check, provide a list of files and/or directories to `flake8`:

    $ flake8 ... | fgrep -v -e E501 -e E203 -e E722

Here `fgrep` is used to ignore E501 (line too long) and E203 (whitespace before ':') as these are rules that Black and Flake8 disagree on. I also ignore E203 (do not use bare 'except') as I'm not prepared to enforce this rule in the code.

Android screen recorder
-----------------------

The [usage video](https://george-hawkins.github.io/micropython-wifi-setup/) was recorded with the open-source [ScreenCam](https://play.google.com/store/apps/details?id=com.orpheusdroid.screenrecorder) using the default settings.

It was edited with [iMovie](https://www.apple.com/imovie/) and exported at 540p / medium quality / best compression.

It was then cropped to size using this SuperUser StackExchange [answer](https://superuser.com/a/810524) like so:

    $ ffmpeg -ss 20 -i wifi-setup2.mp4 -vframes 10 -vf cropdetect -f null -
        Stream #0:0(und): Video: h264 (High) ... 960x540 ...
    [Parsed_cropdetect_0 @ 0x7fa729e00f00] x1:327 x2:632 ... crop=304:528:328:6
    $ ffplay -vf crop=304:540:328:0 wifi-setup3.mp4
    $ ffmpeg -i wifi-setup3.mp4 -vf crop=304:540:328:0 output.mp4

For whatever reason, the suggested cropping was a little over-aggressive (6 pixels at top and bottom) so I manually adjusted the values.
