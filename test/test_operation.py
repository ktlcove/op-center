import logging
import unittest

from op_center.server import user, orm
from op_center.server.controller import Controller
from op_center.server.mq import main_mq
from op_center.server.operation import Operation
from test import async_run

logger = logging.getLogger(__name__)


class TestOperation(unittest.TestCase):

    @async_run
    async def setUp(self):
        self.user = await user.User.login_by_password("local-admin", "admin")
        self.controller = Controller(self.user)
        # wf = await self.controller.create_workflow(name="test22",
        #                                            description="test desc",
        #                                            steps=[], basic={}, envs={}, args={})
        # hf = await self.controller.create_host_filter(name="test22",
        #                                               description="test desc",
        #                                               filters=[
        #                                                   {"idc": {
        #                                                       "in": ["idc1", ],
        #                                                   }},
        #                                                   {"env": {
        #                                                       "is": "test",
        #                                                   }},
        #                                                   {"ip": {
        #                                                       "regexp": "^10\.0\.0\.[0-9]{1,3}$",
        #                                                       "in": ["10.0.0.64", "10.0.0.106"],
        #                                                   }}
        #                                               ])
        #
        # operator = await self.controller.create_operator(name="test22",
        #                                                  description="test desc",
        #                                                  type=OPERATOR_TYPE_CELERY,
        #                                                  mq_link={"address": ["127.0.0.1", 6379],
        #                                                           "db": 13, "password": None})
        #
        # operation = await self.controller.create_operation(
        #     name="test", workflow_id=wf["id"],
        #     operator_id=operator["id"], host_filter_id=hf["id"], auto_fork=True
        # )
        operation = await self.controller.orm_operation.only_or_raise(orm.t.optn.name=="test-http-view2")
        self.operation = Operation(operation, user=self.user, use_cache=True)

    @async_run
    async def test_x(self):

        await self.operation.refresh_cache()

        logger.debug(await self.operation.get_hosts())
        logger.debug(await self.operation.get_workflow())

        task = await self.operation.run({"a":"b"})

        logger.debug(task)
        logger.debug(await main_mq.get_running_task_count())

    @async_run
    async def tearDown(self):
        # await self.controller.orm_operation.query_delete()
        # await self.controller.orm_operator.query_delete()
        # await self.controller.orm_workflow.query_delete()
        # await self.controller.orm_host_filter.query_delete()
        pass

if __name__ == '__main__':
    unittest.main()
