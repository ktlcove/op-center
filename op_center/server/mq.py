import datetime
import json
import logging
import re

from op_center.basic import TASK_STATUS_WAIT, functools, BaseJsonEncoder, cfg, asyncio, TASK_STATUS_QUEUE
from op_center.mq.redis_async_mq import ABCAsyncRedisMQ
from op_center.server import ServerException

logger = logging.getLogger(__name__)


class ServerMQException(ServerException):
    pass


class ServerMQTaskError(ServerMQException):
    pass


class ServerMQError(ServerMQException):
    pass


class RedisJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.timestamp()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return json.JSONEncoder.default(self, obj)


serializer = functools.partial(json.dumps,
                               cls=BaseJsonEncoder,
                               ensure_ascii=False)


class OperatorWorkerAsyncMQ(ABCAsyncRedisMQ):
    """
    worker master / server 与 worker 通信用的 mq
    这里实现master / server的调用部分
    供worker master/ server 控制 worker 使用
    """

    TASK_INFO_PREFIX = "tasK_info_"
    TASK_QUEUE_KEY = "task_queue"
    TASK_STATUS_PREFIX = "task_status_"

    RUNNING_TASKS_KEY = "running_tasks"

    TASK_RESULT_PREFIX = "task_result_"

    MAX_RUNNING_TASKS_KEY = "max_running_tasks"
    MAX_QUEUE_TASKS_KEY = "max_queue_tasks"

    TASK_STATUS_KEY_SPLIT = re.compile(r"^(?P<field>.+)__(?P<action>[^_].+)$")

    def __init__(self, meta: dict):
        super().__init__(link_kwargs=meta['mq_link']["link_kwargs"])
        self.meta = meta
        self.key_prefix = self.meta['name'] + "_"

    async def change_task_status(self, task_id, kwargs):
        """
        ask_status_task_id = {
        "total": int,
        "finish": int,
        "all_status": KEYWORDS.TASK_ALL_STATUS,
        KEYWORDS.TASK_STATUS_WAIT: int,
        KEYWORDS.TASK_STATUS_QUEUE: int,
        ...: ...
        """
        key = self.TASK_STATUS_PREFIX + task_id
        for k, v in kwargs.items():
            tmp = self.TASK_STATUS_KEY_SPLIT.match(k)
            if tmp:
                field = tmp.groupdict().get("field")
                action = tmp.groupdict().get("action")
            else:
                field = k
                action = None
            if not action:
                await self.LINK_POOL.hset(key, field, v)
            else:
                if action == "inc":
                    await self.LINK_POOL.hincrby(key, field, v)
                else:
                    raise RuntimeError(f"action {action} error")

    # @abc.abstractmethod
    # async def run_task_for_one_host(self, *, task_id, workflow, host, running_kwargs):
    #     pass


class Server2WorkerMasterAsyncMQ(ABCAsyncRedisMQ):
    """
    task sample:
    {
        id: xxx
        hosts: [{},{}...],
        workflow: {},
        operator: operator or None , None is auto select
        running_kwargs: {}
        runner: str,
        status: {
            task_status: xxx
            }
        result: {},
        c_time: datetime instance
        m_time: datetime instance
        f_time: None
    }
    """

    TASK_INFO_PREFIX = "tasK_info_"
    TASK_QUEUE_KEY = "task_queue"
    TASK_STATUS_PREFIX = "task_status_"

    RUNNING_TASKS_KEY = "running_tasks"

    TASK_RESULT_PREFIX = "task_result_"

    MAX_RUNNING_TASKS_KEY = "max_running_tasks"
    MAX_QUEUE_TASKS_KEY = "max_queue_tasks"

    TASK_STATUS_KEY_SPLIT = re.compile(r"^(?P<field>.+)__(?P<action>[^_].+)$")

    # running task
    async def get_running_task_ids(self) -> set:
        return await self.LINK_POOL.smembers(self.RUNNING_TASKS_KEY)

    async def get_running_task_count(self) -> int:
        return len(await self.get_running_task_ids())

    async def get_max_running_task_count(self) -> int:
        return int(await self.LINK_POOL.get(self.MAX_RUNNING_TASKS_KEY))

    async def running_task_full_and_raise(self):
        running_task_count = await self.get_running_task_count()
        max_running_task_count = await self.get_max_running_task_count()
        if running_task_count <= max_running_task_count:
            return False
        raise ServerMQError(f"running task is full {running_task_count}/{max_running_task_count}")

    async def running_task_full(self) -> bool:
        running_task_count = await self.get_running_task_count()
        max_running_task_count = await self.get_max_running_task_count()
        if running_task_count <= max_running_task_count:
            return False
        return False

    # task queue
    async def get_queue_task_ids(self) -> list:
        return await self.LINK_POOL.lrange(self.TASK_QUEUE_KEY, start=0,
                                           stop=await self.get_max_queue_task_count())

    async def get_queue_task_count(self):
        return await self.LINK_POOL.llen(self.TASK_QUEUE_KEY)

    async def get_max_queue_task_count(self) -> int:
        return int(await self.LINK_POOL.get(self.MAX_QUEUE_TASKS_KEY))

    async def queue_full_and_raise(self):
        queue_task_count = await self.get_queue_task_count()
        max_queue_task_count = await self.get_max_queue_task_count()
        if queue_task_count <= max_queue_task_count:
            return False
        raise ServerMQError(f"task queue is full {queue_task_count}/{max_queue_task_count}")

    async def get_task_status(self, task_id):
        # if task_info key exist and task not complete can find status in mq
        # if not await self.LINK_POOL.exists(self.TASK_INFO_PREFIX + task_id):
        #     return None
        # else:
        return await self.LINK_POOL.hgetall(self.TASK_STATUS_PREFIX + task_id) or {}

    # task result
    async def get_task_result(self, task_id):
        result = await self.LINK_POOL.hgetall(self.TASK_RESULT_PREFIX + task_id)
        return {ip: json.loads(r) for ip, r in result.items()}

    # task status
    async def change_task_status(self, task_id, kwargs):
        """
        ask_status_task_id = {
        "total": int,
        "finish": int,
        "all_status": KEYWORDS.TASK_ALL_STATUS,
        KEYWORDS.TASK_STATUS_WAIT: int,
        KEYWORDS.TASK_STATUS_QUEUE: int,
        ...: ...
        """
        key = self.TASK_STATUS_PREFIX + task_id
        for k, v in kwargs.items():
            tmp = self.TASK_STATUS_KEY_SPLIT.match(k)
            if tmp:
                field = tmp.groupdict().get("field")
                action = tmp.groupdict().get("action")
            else:
                field = k
                action = None
            if not action:
                await self.LINK_POOL.hset(key, field, v)
            else:
                if action == "inc":
                    await self.LINK_POOL.hincrby(key, field, v)
                else:
                    raise RuntimeError(f"action {action} error")

    async def close_task_by_id(self, task_id):
        # pop task_id from running task collection
        await self.LINK_POOL.srem(self.RUNNING_TASKS_KEY, task_id)
        # delete running task info
        await self.LINK_POOL.delete(self.TASK_INFO_PREFIX + task_id)

    async def set_max_queue_task_count(self, c):
        await self.LINK_POOL.set(self.MAX_QUEUE_TASKS_KEY, c)

    async def set_max_running_task_count(self, c):
        await self.LINK_POOL.set(self.MAX_RUNNING_TASKS_KEY, c)

    async def push_task_to_queue(self, task: dict) -> None or Exception:
        """
        把 task 丢进任务准备队列 server 端转有方法
        task.status.task_status:  wait -> queue
        task_status = origin task status
        task_info_task[id] = task
        task_queue + task[id]
        """
        # check task status
        if task['status']["task_status"] != TASK_STATUS_WAIT:
            raise ServerMQTaskError(f"task {task} status is not wait can't push to queue...")

        # check tasks queue is not full
        await self.queue_full_and_raise()

        # write task info
        await self.LINK_POOL.set(self.TASK_INFO_PREFIX + str(task["id"]), serializer(task))

        # write task origin status
        await self.LINK_POOL.hmset_dict(self.TASK_STATUS_PREFIX + task["id"],
                                        {
                                            "task_status": TASK_STATUS_QUEUE,
                                            "total": len(task["hosts"]),
                                            "finish": 0,
                                            TASK_STATUS_QUEUE: len(task["hosts"]),
                                            TASK_STATUS_WAIT: 0,
                                        })

        # add task_id to task_queue task collection
        await self.LINK_POOL.rpush(self.TASK_QUEUE_KEY, task["id"])

    async def remove_task(self, task_id):
        await self.LINK_POOL.delete(self.TASK_STATUS_PREFIX + task_id)
        await self.LINK_POOL.delete(self.TASK_RESULT_PREFIX + task_id)
        await self.LINK_POOL.srem(self.RUNNING_TASKS_KEY, task_id)

    async def pop_task_or_none(self):
        if await self.running_task_full():
            logger.debug("running task full...")
            return None
        task_id = await self.LINK_POOL.lpop(self.TASK_QUEUE_KEY)
        logger.debug(f"lpop task {task_id} from task_queue")
        if not task_id:
            return None
        task_string = await self.LINK_POOL.get(self.TASK_INFO_PREFIX + task_id)
        if task_string:
            logger.debug(f"get task info {task_id} success")
            try:
                task = json.loads(task_string)
            except json.JSONDecodeError:
                logger.critical(f"json load task {task_id} failure, task_string is --->>> {task_string}")
                return None
            logger.debug(f"json load task {task_id} success")
            await self.LINK_POOL.sadd(self.RUNNING_TASKS_KEY, task_id)
            # await self.LINK_POOL.hmset_dict(self.TASK_STATUS_PREFIX + task_id,
            #                                 {"task_status": TASK_STATUS_,
            #                                  KEYWORDS.TASK_STATUS_QUEUE: 0,
            #                                  KEYWORDS.TASK_STATUS_RUNNING: 0,
            #                                  KEYWORDS.TASK_STATUS_ROUTER: len(task["hosts"])})
            return task
        else:
            logger.critical(f"get task {task_id} is empty...")
            return None

    async def write_host_result(self, task_id, host_ip, result):
        await self.LINK_POOL.hset(self.TASK_RESULT_PREFIX + task_id,
                                  host_ip, result)


main_mq = Server2WorkerMasterAsyncMQ(link_kwargs=cfg["mq"]["main"])
asyncio.get_event_loop().run_until_complete(main_mq.init_mq_conn())
asyncio.get_event_loop().run_until_complete(main_mq.set_max_running_task_count(10))
asyncio.get_event_loop().run_until_complete(main_mq.set_max_queue_task_count(50))
