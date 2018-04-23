import aioredis

from op_center.mq import ABCAsyncMQ


class ABCAsyncRedisMQ(ABCAsyncMQ):
    LINK_POOL = None

    async def init_mq_conn(self):
        if not self.LINK_POOL:
            self.LINK_POOL = await aioredis.create_redis_pool(address=self._link_kwargs["address"],
                                                              db=self._link_kwargs["db"],
                                                              password=self._link_kwargs.get("password", None),
                                                              encoding="utf-8")

    async def available(self):
        if not self.LINK_POOL:
            return False
        else:
            try:
                if await self.LINK_POOL.ping():
                    return True
                return False
            except aioredis.errors.PoolClosedError:
                return False

    async def close(self):
        self.LINK_POOL.close()
        await self.LINK_POOL.wait_closed()

    def __init__(self, link_kwargs=None):
        self._link_kwargs = link_kwargs
