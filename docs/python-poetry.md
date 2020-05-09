Managing MicroPython packages with Poetry
=========================================

This page documents the rather involved steps needed to manage this project and publish it to [PyPI](https://pypi.org/) using [Python Poetry](https://python-poetry.org/).

In the end, I gave up on this idea for the simple reason that MicroPython's [`upip`](https://docs.micropython.org/en/latest/reference/packages.html#upip-package-manager) simply doesn't work at this time, on the ESP32 port, and hasn't worked for quite some time (see MicroPython issue [#5543](https://github.com/micropython/micropython/issues/5543), including one comment from me).

When starting in on this, the difference between a [source distribution](https://docs.python.org/3.7/distutils/sourcedist.html), an egg and a wheel wasn't clear to me (see ["wheel vs egg"](https://packaging.python.org/discussions/wheel-vs-egg/)). And I'm not entirely sure that the distinction between a source distribution and an egg is clear in how MicroPython handle things. The MicroPython documentation says it uses the source distribution format for packaging. However it depends on egg related data included in such a distribution. It's true that [setuptools](https://setuptools.readthedocs.io/en/latest/) includes egg information in a source distribution. However Poetry does not and this appears to be valid. It would probably be clearer if `upip` explicitly worked with eggs rather than with source distributions that happen to contain egg related data.

It took me quite a while to realize that there's a fair degree of mismatch between what Poetry produces and what the MicroPython `upip` package manager.

Poetry creates a source distribution that contains a `setup.py` but does not contain the egg related data that `upip` wants. Poetry has the egg related support it needs for dealing with existing packages, however it only build source distributions (without egg related data) and the newer wheel format.

`upip` depends on [`setuptool.setup`](https://setuptools.readthedocs.io/en/latest/setuptools.html), in your project's `setup.py`, being run with `cmdclass` set to bind `sdist` to the version provided by [`sdist_upip.py`](https://github.com/micropython/micropython-lib/blob/master/sdist_upip.py) (see the [documentation](https://docs.micropython.org/en/latest/reference/packages.html#creating-distribution-packages)). This results in a source distribution with a custom compression size and with `setup.py` excluded from the bundle (see [here](https://docs.micropython.org/en/latest/reference/packages.html#distribution-packages). Poetry auto-generates a `setup.py` when building a source distribution and bundles it in with the distribution. However the `setup.py` isn't executed at this point (it's only executed later by `pip` when _installing_ the distribution) so it can't affect e.g. the compression or anything else.

Given all that, let's see how I got to a point where I could create and publish MicroPython compatible packages to PyPI. However, if I was doing this again I would create `setup.py` by hand and not introduce Poetry into the mix.

Installation
------------

I installed Poetry as per the [installation instructions](https://python-poetry.org/docs/#installation):

```
$ curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
$ poetry completions bash | sudo tee /etc/bash_completion.d/poetry.bash-completion > /dev/null
$ poetry init
$ poetry check
```

If you're using venv then Poetry will use this, however if one isn't currently active, Poetry will use its own venv management mechanism (creating venvs under `~/.cache/pypoetry/virtualenvs` on Linux).

I prefer to use the standard mechanism:

```
$ python3 -m venv env
$ source env/bin/activate
$ pip install --upgrade pip
```

Then to create a Poetry `pyproject.toml` run and complete the questions asked by:

```
$ poetry init
Package name [foo-bar]:  
Version [0.1.0]:  
Description []:  
Author [George Hawkins <foo@bar.com>, n to skip]:  George Hawkins
License []:  MIT
Compatible Python versions [^3.6]:  
Would you like to define your main dependencies interactively? (yes/no) [yes] 
...
Search for package to add (or leave blank to continue): micropython-logging
...
Enter the version constraint to require (or leave blank to use the latest version): 
Using version ^0.5.2 for micropython-logging
Add a package: 
Would you like to define your development dependencies interactively? (yes/no) [yes] no
...
Do you confirm generation? (yes/no) [yes]
```

Note: it's fine to exclude your email address for the `Author` field (although setuptools does generate a warning if it's not present).

Normally, you'd then do:

```
$ poetry install
```

However, as noted later this won't work as MicroPython dependencies, like micropython-logging, aren't installable.

The install process would produce a `poetry.lock` file. If your project is not a library then you should checkin the `poetry.lock` created by Poetry, however for a library you should not (see [here](https://python-poetry.org/docs/libraries/#lock-file)).

Note that the `build` and `publish` steps, covered later, don't depend on `install` having been run or having succeeded.

PyPI token
----------

I [registered](https://pypi.org/account/register/) for a PyPI account and, once logged in, created a [token](https://pypi.org/manage/account/token/) called "pypi" (the name is unimportant, it's just used to identify the token, in the list shown on your main account page where you can revoke it later if needed) with a scope of _Entire account_.

I saved displayed token to `~/pypi-token` and then, as per the Poetry configuring credentials [instructions](https://python-poetry.org/docs/repositories/#configuring-credentials):

```
poetry config pypi-token.pypi $(< ~/pypi-token)
```

Usually `config` entries end up in your global Poetry config file (on Linux, it's `.config/pypoetry/config.toml`, for other platforms see [here](https://python-poetry.org/docs/configuration/)). However for tokens Poetry uses [keyring](https://pypi.org/project/keyring/) to store this value in your system's keyring service.

Building and publishing
-----------------------

In your `.toml` file you should name your project with minuses for spaces, e.g. `name = "foo-bar"`, however everywhere else these minuses become underscores, e.g. the corresponding subdirectory name is `foo_bar`.

Minimal project layout:

```
pyproject.toml
foo_bar
+-- foo.py
```

Then to build a source distribution - `sdist` - and a wheel:

```
$ poetry build
```

This generates a `dist` subdirectory (which you should add to `.gitignore`).

Then you can publish it to PyPI:

```
$ poetry publish
```

Your project is available on PyPI and, if logged in, you can find it under your [projects](https://pypi.org/manage/projects/).

Problems begin
--------------

Unfortunately, if any of your dependencies are MicroPython ones you can't install the resulting package because you simple can't install the dependencies, e.g. try directly installing something like micropython-logging:

```
$ pip install micropython-logging
...
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/pip-install-kfqm4aru/micropython-logging/setup.py'
...
```

As noted [here](http://docs.micropython.org/en/latest/reference/packages.html) MicroPython packages don't include the expected `setup.py`.

You can only install such packages using `upip`:

```
$ micropython -m upip install -p lib micropython-logging
Installing to: lib/
...
Installing micropython-logging 0.3 from https://micropython.org/pi/logging/logging-0.3.tar.gz
```

Pyenv and MicroPython
---------------------

Above, I use `micropython` on Linux. If you've already installed MicroPython with `pyenv`, can enable CPython and MicroPython versions at the same time:

```
$ pyenv global 3.6.9 micropython-1.12
```

Addressing the issues
---------------------

`upip` expects just to see a single format available on PyPI and chokes if it sees more than one - so if immediately fails on seeing both the sdist and wheel packages published by Poetry.

You can force Poetry only to build the sdist package like this:

```
$ poetry build --format=sdist
```

I thought I would be able to disable building the wheel package via the `pyproject.toml` however adding the following didn't work as expected:

```
packages = [
    { include = "foo_bar_cb3da32", format = "sdist" },
]
```

Note that you use the underscore variant of the package name, this was the first thing that got me. However, this does not disable building of the wheel, see issue [#2365](https://github.com/python-poetry/poetry/issues/2365) that I logged against Poetry.

Note also that unfortunately, the [documentation](https://python-poetry.org/docs/pyproject/#packages) states:

> Using packages disables the package auto-detection feature meaning you have to explicitly specify the "default" package.

Aside: another interesting thing you can do with `packages` is specify that a package is in a non-standardly named directory, e.g. `{ include = "my_package", from = "lib" }`.

---

Next it turns out that while `upip` works with source distributions, it depends on the egg related information that setuptools includes in a source distribution but which Poetry does not. In particular it expects to find a file of the form `foo_bar.egg-info/requires.txt` that contains the dependencies of your project (see [`upip.py:92](https://github.com/micropython/micropython/blob/69661f3/tools/upip.py#L92)).

You can generate `requires.txt` by hand and it will be included in your sdist package - this is enough to keep `upip` happy.

However, you can also get Poetry to create a `setup.py` which can be used to generate `requires.txt`. First:

```
$ poetry build --format=sdist
$ name=foo-bar-0.1.0
$ tar --to-stdout -xf dist/$name.tar.gz $name/setup.py > setup.py
```

Now use `setup.py` to generate the egg information:

```
$ python setup.py sdist
```

Setuptools automatically generates the egg information that Poetry does not. You can also ask setuptools to only generate the egg information (and not a full source distribution) like so:

```
$ python setup.py egg_info
```

The `requires.txt` file will contain any version contraints specified in the `.toml` file, however `upip` cannot handle these contraints and they should be removed (as shown in the fully worked example later).

Once you have a generataed or hand-crafted `requires.txt`, Poetry will include it in the sdist package that it creates and this is enough to convince the UNIX port of `upip` to accept your package (published to PyPI _without_ the corresponding wheel) and install it along with its dependencies:

```
$ micropython -m upip install -p lib foo-bar-cb3da32
Installing to: lib/
Warning: micropython.org SSL certificate is not validated
Installing foo-bar-cb3da32 0.1.5 from https://files.pythonhosted.org/packages/a9/17/7373487a933881dcaa93e7fb3b11bdd7966799620f84c211c42ec0ad9760/foo-bar-cb3da32-0.1.5.tar.gz
Installing micropython-logging 0.3 from https://micropython.org/pi/logging/logging-0.3.tar.gz
```

However, it will still fail on other MicroPython ports as it wasn't produced by `sdist_upip.sdist` with the required compression size etc.

Upip fails on the ESP32 port
----------------------------

Anyway at the moment `upip` on the ESP32 port fails for everything:

```
$  rshell -p $PORT --buffer-size 512 --quiet
> repl
>>> import network
>>> wlan = network.WLAN(network.STA_IF)
>>> wlan.active(True)
>>> wlan.connect('MyWiFiNetwork', 'MyWiFiPassword')
>>> import upip
>>> upip.install('micropython-logging')
Installing to: /lib/
I (183850) wifi: bcn_timout,ap_probe_send_start
I (186350) wifi: ap_probe_send over, resett wifi status to disassoc
I (186350) wifi: state: run -> init (c800)
I (186350) wifi: pm stop, total sleep time: 47458331 us / 60262159 us

I (186350) wifi: new:<1,0>, old:<1,0>, ap:<255,255>, sta:<1,0>, prof:1
mbedtls_ssl_handshake error: -71
I (186360) wifi: STA_DISCONNECTED, reason:200
beacon timeout
Error installing 'micropython-logging': [Errno 5] EIO, packages may be partially installed
>>>
```

It seem `upip` hasn't worked on the ESP32 port of MicroPython for quite some time - see [#5543](https://github.com/micropython/micropython/issues/5543).

So this make publishing to PyPI a rather moot point (except that one uses the UNIX port).

Putting it altogether
---------------------

However, given all that it is possible to build and publish a package to PyPI, using Poetry, that could be installed if `upip` currently worked on the ESP32 port. The following is a fully worked example.

Create the `foo-bar` project directory and setup a venv:

```
$ mkdir foo-bar
$ cd foo-bar
$ python3 -m venv env
$ source env/bin/activate
$ pip install --upgrade pip
```

Create the project content:

```
$ mkdir foo_bar
$ echo 'print("foo-bar")' > foo_bar/foo.py
```

Create the `pyproject.toml` (with `micropython-logging` as a single simple dependency):

```
$ poetry init
Package name [foo-bar]:
Version [0.1.0]:
Description []:
Author [George Hawkins <george-hawkins@users.noreply.github.com>, n to skip]:  George Hawkins
License []:  MIT
Compatible Python versions [^3.6]:
Would you like to define your main dependencies interactively? (yes/no) [yes]
...
Search for package to add (or leave blank to continue): micropython-logging
...
Enter the version constraint to require (or leave blank to use the latest version):
Add a package:
Would you like to define your development dependencies interactively? (yes/no) [yes] no
...
Do you confirm generation? (yes/no) [yes]
```

As note above, `upip` can't handle version constraints so you have to edit `pyproject.toml` and change the contraint for `micropython-logging` from `"^0.5.2"` to just `""`:

```
$ vim pyproject.toml
```

Produce a source distribution and extract the `setup.py` file from it:

```
$ poetry build --format=sdist
$ name=foo-bar-0.1.0
$ tar --to-stdout -xf dist/$name.tar.gz $name/setup.py > setup.py
```

Edit it to include `import sdist_upip` and `'cmdclass': {{'sdist': sdist_upip.sdist}},` as per the MicroPython [instructions](http://docs.micropython.org/en/latest/reference/packages.html#creating-distribution-packages):

```
$ vim setup.py
```

Download the `sdist_upip.py` that's now needed by `setup.py` as a result of our changes:

```
$ curl -O https://raw.githubusercontent.com/micropython/micropython-lib/master/sdist_upip.py
```

Now get setuptools, rather than Poetry to regenerate the source distribution:

```
$ python setup.py sdist
```

You can no get Poetry to publish this to PyPI:

```
$ poetry publish 
```

And the UNIX port of MicroPython can install it and its dependencies:

```
$ micropython -m upip install -p lib foo-bar
```

As could any other _working_ port of `upip`.

In the end, it's all a bit pointless and as you can see from the above example it would be easier to create `setup.py` directly, work with it and leave Poetry out of the equation.

Notes
-----

If you wanted to add the ability to automatically add `cmdclass` to `setup.py` you'd have to modify the behavior around the `SETUP` string in [`poetry/masonry/builders/sdist.py`](https://github.com/python-poetry/poetry/blob/master/poetry/masonry/builders/sdist.py).

Remember that if you do submit a Poetry pull-request related to this, and it gets accepted, you'd need to set the minimum Poetry version appropriately in the `.toml` file, i.e. change the line:

```
requires = ["poetry>=0.12"]
```

I asked whether Poetry can produce eggs [here](https://discordapp.com/channels/487711540787675139/487711540787675143/70506829603405836) on their Discord channel - but never received any follow-up. I don't believe it can.
