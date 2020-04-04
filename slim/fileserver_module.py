from slim.shim import isdir, exists


class FileserverModule:
    _DEFAULT_PAGE = "index.html"

    def __init__(self, mime_types, root="www"):
        self._mime_types = mime_types
        self._root = root

    def OnRequest(self, request):
        if request.IsUpgrade or request.Method not in ("GET", "HEAD"):
            return

        filename = self._resolve_physical_path(request.Path)
        if filename:
            ct = self._get_mime_type_from_filename(filename)
            if ct:
                request.Response.AllowCaching = True
                request.Response.ContentType = ct
                request.Response.ReturnFile(filename)
            else:
                request.Response.ReturnForbidden()
        else:
            request.Response.ReturnNotFound()

    def _resolve_physical_path(self, url_path):
        if ".." in url_path:
            return None  # Don't allow trying to escape the root.

        if url_path.endswith("/"):
            url_path = url_path[:-1]
        path = self._root + url_path
        if isdir(path):
            path = path + "/" + self._DEFAULT_PAGE

        return path if exists(path) else None

    def _get_mime_type_from_filename(self, filename):
        def ext(name):
            partition = name.rpartition(".")
            return None if partition[0] == "" else partition[2].lower()

        return self._mime_types.get(ext(filename), None)