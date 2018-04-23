import abc
import asyncio

loop = asyncio.get_event_loop()


def run(future):
    return loop.run_until_complete(future)


class ABCCrontab(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return run(self.run(*args, **kwargs))