import asyncio
import functools

loop = asyncio.get_event_loop()


def async_run(f):
    @functools.wraps(f)
    def real_func(*args, **kwargs):
        return loop.run_until_complete(f(*args, **kwargs))

    return real_func
