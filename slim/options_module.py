class OptionsModule:
    def __init__(self, cors_allow_all=False):
        self._cors_allow_all = cors_allow_all

    def OnRequest(self, request):
        if request.IsUpgrade or request.Method != "OPTIONS":
            return

        if self._cors_allow_all:
            request.Response.SetHeader("Access-Control-Allow-Methods", "*")
            request.Response.SetHeader("Access-Control-Allow-Headers", "*")
            request.Response.SetHeader("Access-Control-Allow-Credentials", "true")
            request.Response.SetHeader("Access-Control-Max-Age", "86400")
        request.Response.ReturnOk()