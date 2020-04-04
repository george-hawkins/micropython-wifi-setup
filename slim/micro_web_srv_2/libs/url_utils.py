# The MIT License (MIT)
# Copyright 2019 Jean-Christophe Bos & HC2 (www.hc2.fr)


class UrlUtils:

    # ----------------------------------------------------------------------------

    @staticmethod
    def Unquote(s):
        r = str(s).split("%")
        try:
            b = r[0].encode()
            for i in range(1, len(r)):
                try:
                    b += bytes([int(r[i][:2], 16)]) + r[i][2:].encode()
                except:
                    b += b"%" + r[i].encode()
            return b.decode("UTF-8")
        except:
            return str(s)

    # ----------------------------------------------------------------------------

    @staticmethod
    def UnquotePlus(s):
        return UrlUtils.Unquote(str(s).replace("+", " "))

    # ============================================================================
    # ============================================================================
    # ============================================================================
