import asyncio
import logging

import sqlalchemy.exc

from op_center.basic import TASK_STATUS_FINISH, Now
from op_center.server import orm
from op_center.server.mq import main_mq
from op_center.server.operator import operator_manager

logger = logging.getLogger(__name__)


class WorkerMaster:
    """
    后台管理者。 负责把queue里的task搞出来丢给后端worker
    对应task status变化 queue -> router
    """

    @property
    def mq(self):
        return self._mq

    def __init__(self):
        self._mq = main_mq
        self._check_delay = 1
        self.loop = asyncio.get_event_loop()
        self.working_on = False
        self.worker = None
        self.operator_manager = operator_manager

    async def link_start(self):
        await self.mq.init_mq_conn()
        logger.debug("worker master mq link start ok")

    async def task_generator(self):
        logger.debug(f"task_generator start...")
        while self.working_on:
            task = await self.mq.pop_task_or_none()
            if task:
                logger.debug(f"get task {task['id']} ...")
                yield task
                continue
            else:
                logger.debug(f"get task {task}...")
                await asyncio.sleep(self._check_delay)
        logger.debug(f"task_generator exit...")

    async def _work_loop(self):
        logger.debug(f"task work loop start...")
        generator = self.task_generator()
        async for task in generator:
            logger.debug(f"create future for task {task['id']}...")
            asyncio.ensure_future(self.do_task(task))
            asyncio.ensure_future(self.hold_task(task["id"]))
        logger.debug("task work loop closed...")

    async def work_start(self):
        logger.debug("worker master start")
        self.working_on = True
        await self.link_start()
        self.worker = asyncio.ensure_future(self._work_loop(), loop=self.loop)

    async def do_task(self, task):
        logger.debug(f"do task {task}")
        await self.operator_manager.run_task(task)

    async def close(self):
        if self.working_on:
            self.working_on = False
            await self.worker
        logger.debug(f"worker master closed")

    async def hold_task(self, task_id):
        while True:
            await asyncio.sleep(1)
            status = await self.mq.get_task_status(task_id) or {}
            logger.debug(f"hold task {task_id} status is {status}")
            total = status.get("total", None)
            finish = status.get(TASK_STATUS_FINISH, None)
            if total is not None and finish is not None and total == finish:
                logger.info(f"hold task {task_id} {finish}/{total} task done...")
                await self.mq.change_task_status(task_id, dict(task_status=TASK_STATUS_FINISH))
                await self.task_done(task_id)
                logger.info(f"task {task_id} done and exit this task holder")
                break

    async def task_done(self, task_id):
        logger.debug(f"now do archive task {task_id}")
        for i in range(3):
            try:
                task_orm = orm.Task()
                await task_orm.query_update(orm.t.tsk.id == task_id,
                                            status=await self.mq.get_task_status(task_id),
                                            result=await self.mq.get_task_result(task_id),
                                            f_time=Now().instance())
            except sqlalchemy.exc.OperationalError:
                logger.critical(f"task {task_id} archive failure {i}")
                continue

        await self.mq.remove_task(task_id)
        logger.debug(f"task {task_id} archive ok...")

    def run_forever(self):
        self.loop.run_until_complete(self.work_start())
        self.loop.run_forever()
