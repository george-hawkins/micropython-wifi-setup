import errno
import btree
import logging

_logger = logging.getLogger("credentials")


# Credentials uses `btree` to store and retrieve data. In retrospect it would
# probably have been at least as easy to just write and read it as JSON.
class Credentials:
    _SSID = b"ssid"
    _PASSWORD = b"password"
    _CREDENTIALS = "credentials"

    def __init__(self, filename=_CREDENTIALS):
        self._filename = filename

    def get(self):
        def action(db):
            ssid = db.get(self._SSID)
            password = db.get(self._PASSWORD)

            return (ssid, password) if ssid else (None, None)

        return self._db_action(action)

    def put(self, ssid, password):
        def action(db):
            db[self._SSID] = ssid
            if password:
                db[self._PASSWORD] = password
            else:
                self._pop(db, self._PASSWORD, None)

        self._db_action(action)

    def clear(self):
        def action(db):
            self._pop(db, self._SSID, None)
            self._pop(db, self._PASSWORD, None)

        self._db_action(action)

    def _db_action(self, action):
        with self._access(self._filename) as f:
            db = btree.open(f)  # Btree doesn't support `with`.
            try:
                return action(db)
            finally:
                # Note that closing the DB does a flush.
                db.close()

    # `btree` doesn't support the standard dictionary `pop`.
    @staticmethod
    def _pop(d, key, default):
        if key in d:
            r = d[key]
            del d[key]
            return r
        else:
            return default

    # Open or create a file in binary mode for updating.
    @staticmethod
    def _access(filename):
        # Python `open` mode characters are a little non-intuitive.
        # For details see https://docs.python.org/3/library/functions.html#open
        try:
            return open(filename, "r+b")
        except OSError as e:
            if e.args[0] != errno.ENOENT:
                raise e
            _logger.info("creating %s", filename)
            return open(filename, "w+b")
