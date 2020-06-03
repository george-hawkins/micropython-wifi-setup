from os import stat


# This file contains functions and constants that exist in CPython but don't exist in MicroPython 1.12.


# os.stat.S_IFDIR.
S_IFDIR = 1 << 14


# os.path.exists.
def exists(path):
    try:
        stat(path)
        return True
    except:
        return False


# os.path.isdir.
def isdir(path):
    return exists(path) and stat(path)[0] & S_IFDIR != 0


# pathlib.Path.read_text.
def read_text(filename):
    with open(filename, "r") as file:
        return file.read()


# Note: `join`, `split` and `dirname` were copied from from https://github.com/micropython/micropython-lib/blob/master/os.path/os/path.py


# os.path.join.
def join(*args):
    # TODO: this is non-compliant
    if type(args[0]) is bytes:
        return b"/".join(args)
    else:
        return "/".join(args)


# os.path.split.
def split(path):
    if path == "":
        return "", ""
    r = path.rsplit("/", 1)
    if len(r) == 1:
        return "", path
    head = r[0]  # .rstrip("/")
    if not head:
        head = "/"
    return head, r[1]


# os.path.dirname.
def dirname(path):
    return split(path)[0]
