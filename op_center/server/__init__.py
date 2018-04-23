import abc

from op_center import basic

from op_center.basic import BasicException


class ServerException(BasicException):
    pass




class Object(basic.Object, metaclass=abc.ABCMeta):
    pass
