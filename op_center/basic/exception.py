class BasicException(Exception):

    code = 500

    @property
    def type(self):
        return self.__class__.__name__

    @property
    def msg(self):
        return str(self)


class BasicSelfException(BasicException):
    pass
