import logging
import unittest

from op_center.basic import OPERATOR_TYPE_CELERY_REDIS
from op_center.server import orm
from op_center.server.controller import Controller
from op_center.server.controller.controller import UnsupportedOperation
from op_center.server.controller.exception import ControllerException
from op_center.server.host_filter import HostFilterException
from op_center.server.user import User
from test import async_run

logger = logging.getLogger(__name__)


class TestController(unittest.TestCase):

    @async_run
    async def setUp(self):
        self._user = await User.login_by_password("local-admin", "admin")
        self.controller = Controller(self._user)

    @async_run
    async def test_mk_update_dict(self):
        update_dict = {"a": 1, "b": None, "c": False}
        default_result = self.controller.mk_update_dict(**update_dict)
        self.assertDictEqual(default_result, {"a": 1, "c": False})
        costom_result = self.controller.mk_update_dict(_ignores=[1], **update_dict)
        self.assertDictEqual(costom_result, {"b": None, "c": False})

    @async_run
    async def test_host_filter(self):
        hf = await self.controller.create_host_filter(name="test",
                                                      description="test desc",
                                                      filters=[
                                                          {"idc": {
                                                              "in": ["idc1", ],
                                                          }},
                                                          {"env": {
                                                              "is": "test",
                                                          }},
                                                          {"ip": {
                                                              "regexp": "^10\.0\.0\.[0-9]{1,2}$",
                                                              "in": ["10.0.0.64", "10.0.0.106"],
                                                          }}
                                                      ])
        logger.info(hf)
        self.assertIsInstance(hf, dict)
        with self.assertRaises(HostFilterException):
            await self.controller.update_host_filter(hf["id"], name="new test", filters=[
                {"not exist": {
                    "in": ["idc1", ],
                }}
            ])

        with self.assertRaises(ControllerException):
            await self.controller.update_host_filter(hf["id"], name="new test", filters=[])
        hf_fork = await self.controller.fork_host_filter(hf["id"])
        await self.controller.delete_host_filter(hf["id"])
        await self.controller.delete_host_filter(hf_fork["id"])

    @async_run
    async def test_workflow(self):
        wf = await self.controller.create_workflow(name="test",
                                                   description="test desc",
                                                   steps=[], basic={}, envs={}, args={})
        logger.debug(wf)
        self.assertIsInstance(wf, dict)
        await self.controller.update_workflow(id=wf['id'], name="test2")
        wf_fork = await self.controller.fork_workflow(wf["id"])
        self.assertIsInstance(wf_fork, dict)
        await self.controller.get_workflow()
        logger.debug(wf_fork)
        await self.controller.delete_workflow(wf["id"])
        await self.controller.delete_workflow(wf_fork["id"])

    @async_run
    async def test_operator(self):
        meta = await self.controller.create_operator(name="test",
                                                     description="test desc",
                                                     type=OPERATOR_TYPE_CELERY_REDIS,
                                                     mq_link={"address": ["127.0.0.1", 6379],
                                                              "db": 13, "password": None})
        logger.debug(meta)
        self.assertIsInstance(meta, dict)
        await self.controller.update_operator(id=meta['id'], name="test2")
        await self.controller.get_operator()
        # with self.assertRaises(UnsupportedOperation):
        #     await self.controller.delete_operator(meta["id"])
        await self.controller.orm_operator.query_delete(orm.t.optr.id == meta["id"])

    @async_run
    async def test_operation(self):
        wf = await self.controller.create_workflow(name="test22",
                                                   description="test desc",
                                                   steps=[], basic={}, envs={}, args={})
        hf = await self.controller.create_host_filter(name="test22",
                                                      description="test desc",
                                                      filters=[
                                                          {"idc": {
                                                              "in": ["idc1", ],
                                                          }},
                                                          {"env": {
                                                              "is": "test",
                                                          }},
                                                          {"ip": {
                                                              "regexp": "^10\.0\.0\.[0-9]{1,3}$",
                                                              "in": ["10.0.0.64", "10.0.0.106"],
                                                          }}
                                                      ])

        operator = await self.controller.create_operator(name="test22",
                                                         description="test desc",
                                                         type=OPERATOR_TYPE_CELERY_REDIS,
                                                         mq_link={"address": ["127.0.0.1", 6379],
                                                                  "db": 13, "password": None})

        operation = await self.controller.create_operation(
            name="test", workflow_id=wf["id"],
            operator_id=operator["id"], host_filter_id=hf["id"], auto_fork=True
        )
        logger.debug(operation)
        self.assertIsInstance(operation, dict)
        await self.controller.operation_refresh_cache(operation["id"])
        await self.controller.delete_operation(operation["id"])

    @async_run
    async def tearDown(self):
        await self.controller.orm_operation.query_delete(True)
        await self.controller.orm_operator.query_delete()
        await self.controller.orm_workflow.query_delete()
        await self.controller.orm_host_filter.query_delete()


if __name__ == '__main__':
    unittest.main()
