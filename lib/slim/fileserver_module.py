import logging

from shim import isdir, exists


_logger = logging.getLogger("fileserver_module")


class FileserverModule:
    _DEFAULT_PAGE = "index.html"

    def __init__(self, mime_types, root="www"):
        self._mime_types = mime_types
        self._root = root

    def OnRequest(self, request):
        if request.IsUpgrade or request.Method not in ("GET", "HEAD"):
            return

        (filename, compressed) = self._resolve_physical_path(request.Path)
        if filename:
            ct = self._get_mime_type_from_filename(filename)
            if ct:
                request.Response.AllowCaching = True
                request.Response.ContentType = ct

                if compressed:
                    request.Response.SetHeader("Content-Encoding", "gzip")
                    filename = compressed
                request.Response.ReturnFile(filename)
            else:
                _logger.warning("no MIME type for %s", filename)
                request.Response.ReturnForbidden()
        else:
            request.Response.ReturnNotFound()

    def _resolve_physical_path(self, url_path):
        if ".." in url_path:
            return None, None  # Disallow trying to escape the root.

        if url_path.endswith("/"):
            url_path = url_path[:-1]
        path = self._root + url_path

        if isdir(path):
            path = path + "/" + self._DEFAULT_PAGE

        if exists(path):
            return path, None

        compressed = path + ".gz"

        # The tuple parentheses aren't optional here.
        return (path, compressed) if exists(compressed) else (None, None)

    def _get_mime_type_from_filename(self, filename):
        def ext(name):
            partition = name.rpartition(".")
            return None if partition[0] == "" else partition[2].lower()

        return self._mime_types.get(ext(filename), None)
