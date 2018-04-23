import redis

from op_center.mq import ABCSyncMQ


class ABCSyncRedisMQ(ABCSyncMQ):
    LINK_POOL = None

    def init_mq_conn(self):
        if not self.LINK_POOL:
            self.LINK_POOL = redis.ConnectionPool(host=self._link_kwargs["address"][0],
                                                  port=self._link_kwargs["address"][1],
                                                  db=self._link_kwargs["db"],
                                                  password=self._link_kwargs.get("password", None),
                                                  encoding="utf-8")
        if not self.conn:
            self.conn = self.get_connection()

    def get_connection(self):
        return redis.Redis(connection_pool=self.LINK_POOL)

    def available(self):
        if not self.LINK_POOL:
            return False
        else:
            try:
                conn = self.get_connection()
                if conn.ping():
                    return True
                return False
            except Exception:
                raise

    def close(self):
        self.LINK_POOL.disconnect()

    def __init__(self, link_kwargs=None):
        self._link_kwargs = link_kwargs
        self.conn = None


class ABCSyncRedisOneLinkMQ(ABCSyncMQ):

    def available(self):
        try:
            if self.conn.ping():
                return True
            return False
        except Exception:
            raise

    def close(self):
        pass

    def __init__(self, link_kwargs=None):
        self._link_kwargs = link_kwargs
        self.conn = redis.Redis(host=self._link_kwargs["address"][0],
                                port=self._link_kwargs['address'][1],
                                db=self._link_kwargs["db"],
                                password=self._link_kwargs["password"])
