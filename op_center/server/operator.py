import abc
import asyncio
import logging

import celery

from op_center.basic import OPERATOR_TYPE_CELERY_REDIS, TASK_STATUS_RUNNING, CELERY_TASK_NAME, TASK_STATUS_QUEUE, \
    TASK_STATUS_ROUTER
from op_center.server import Object, ServerException, orm
from op_center.server.mq import OperatorWorkerAsyncMQ, main_mq

logger = logging.getLogger(__name__)


class OperatorException(ServerException):
    pass


class ABCOperator(Object):
    """
    实际操作者在op-center内的操作对象
    """
    ALL_OPERATORS = {}
    MQ_CLASS = OperatorWorkerAsyncMQ

    @property
    def mq(self):
        return self._mq

    def __init__(self, meta, loop=None):
        super().__init__(meta, loop=loop)
        self.name = meta["name"]
        self._available = True
        self._mq = self.MQ_CLASS(meta)

    async def initialize(self):
        await self.mq.init_mq_conn()

    async def available(self):
        return self._available and await self.mq.available()

    async def close(self):
        self._available = False
        await self.mq.close()

    @abc.abstractmethod
    async def open_task_for_one_host(self, *, task_id, host, workflow, running_kwargs):
        pass


def operator_type_register(o_type):
    def wraps(cls):
        ABCOperator.ALL_OPERATORS[o_type] = cls
        return cls

    return wraps


@operator_type_register(OPERATOR_TYPE_CELERY_REDIS)
class CeleryRedisOperator(ABCOperator):

    def __init__(self, meta, loop=None):
        super().__init__(meta, loop=loop)

        self.celery_app = celery.Celery(broker=self.meta["mq_link"]["broker"],
                                        backend=self.meta["mq_link"]["backend"])

    async def open_task_for_one_host(self, *, task_id, host, workflow, running_kwargs):
        logger.debug(f'{self.name} open task for host {host["ip"]} start ->\n'
                     f'task_id: {task_id}\n'
                     f'workflow: {workflow}\n'
                     f'running_kwargs: {running_kwargs}')
        """
        在这调用 celery.function.delay(task_id, host, workflow, running_kwargs)
        """
        self.celery_app.send_task(name=CELERY_TASK_NAME,
                                  kwargs={
                                      "task_id": task_id,
                                      "host": host,
                                      "workflow": workflow,
                                      "running_kwargs": running_kwargs
                                  }) #, task_id=task_id + "---" + host["ip"])


class OperatorManager:

    @property
    def mq(self):
        return self._mq

    @property
    def orm_operator(self):
        return orm.Operator()

    async def get_operator_by_id(self, id) -> ABCOperator:
        if id not in self.operators:
            meta = await self.orm_operator.only_or_none(orm.t.optr.id == id)
            if not meta:
                raise OperatorException(f"operator(id={id} not found)")
            operator_cls = ABCOperator.ALL_OPERATORS.get(meta["type"], None)
            if not operator_cls:
                raise OperatorException(f"this type({meta['type']})'s operator is unusable")
            self.operators[id] = operator_cls(meta)
            await self.operators[id].initialize()
        return self.operators[id]

    def __init__(self):
        self.operators = {}
        self._mq = main_mq

    async def set_default_operator(self, id):
        self.operators[None] = self.operators[id]

    async def run_task(self, task: dict):
        logger.debug(f"start task: {task}")
        """
        :param task:
        {
            id: xxxxx
            hosts: []
            workflow: {}
            running_kwargs: {}
            operator_id: operator_id or None
        }
        """

        await self.mq.change_task_status(task["id"], {"task_status": TASK_STATUS_RUNNING,
                                                      TASK_STATUS_QUEUE: 0,
                                                      TASK_STATUS_ROUTER: len(task['hosts'])})

        for host in task["hosts"]:
            asyncio.ensure_future(self.open_task_for_one_host(task_id=task["id"],
                                                              host=host, workflow=task["workflow"],
                                                              running_kwargs=task["running_kwargs"],
                                                              operator_id=task['operator_id']))

    async def open_task_for_one_host(self, *, task_id, host, workflow, running_kwargs, operator_id=None):
        operator = await self.get_operator_by_id(operator_id)
        await operator.open_task_for_one_host(task_id=task_id, host=host,
                                              workflow=workflow, running_kwargs=running_kwargs)


operator_manager = OperatorManager()
