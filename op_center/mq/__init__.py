import abc

from op_center.basic import BasicException


class MQException(BasicException):
    pass


class ABCSyncMQ(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def available(self) -> bool:
        pass

    @abc.abstractmethod
    def close(self):
        pass


class ABCAsyncMQ(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def available(self) -> bool:
        pass

    @abc.abstractmethod
    async def close(self):
        pass
