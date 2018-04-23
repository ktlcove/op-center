import asyncio

loop = asyncio.get_event_loop()


def run(future):
    return loop.run_until_complete(future)
