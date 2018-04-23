import collections
import logging
import uuid

from op_center.basic import TASK_STATUS_QUEUE, TASK_STATUS_WAIT, TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE, \
    TASK_RETURN_CODE_UNKNOWN
from op_center.server import orm, ServerException, host_filter
from op_center.server.mq import main_mq

logger = logging.getLogger(__name__)


class TaskException(ServerException):
    pass


class Task(orm.OrmObject):
    __ORM__ = orm.Task

    @property
    def orm_operation(self):
        return orm.Operation(self.orm_session)

    @property
    def mq(self):
        return main_mq

    # def __init__(self, meta: dict, loop=None, orm_session=None):
    #     super().__init__(meta, loop=loop)
    #     self.orm_session = orm_session or DBSession()
    #     self._orm_instance = self.__ORM__(session=self.orm_session)

    @classmethod
    async def create_by_id(cls, id, loop=None, orm_session=None):
        orm_session = orm_session or orm.DBSession()
        orm_instance = orm.Task(session=orm_session)
        task = await orm_instance.only_or_raise(orm.t.tsk.id == id)
        if task["status"]["task_status"] == TASK_STATUS_QUEUE \
                or task["status"]["task_status"] == TASK_STATUS_WAIT:
            queue_status = await main_mq.get_task_status(task_id=id)
            queue_result = await main_mq.get_task_result(task_id=id)
            task["status"] = queue_status
            task["result"] = queue_result
        return cls(task, loop=loop, orm_session=orm_session)

    async def parse_task_result(self, **kwargs):
        """
        cost_gt int
        cost_lt int
        finish  bool
        success bool
        failure bool
        code    int
        retry   int
        """
        empty_result = {
            "status": None,
            "c_time": None,
            "f_time": None,
            "worker": None,
            "history": [],
            "code": None,
            "stdout": None,
            "stderr": None,
        }
        hosts = self.meta["hosts"]

        if "cost_gt" in kwargs or "cost_lt" in kwargs:
            if "finish" in kwargs and not kwargs["finish"]:
                raise TaskException("query by cost time need finish = True")
            kwargs["finish"] = True

        # create dict to save result
        result = {
            "count": 0,
            "ips": [],
            "details": {},
        }

        for ip in hosts:

            # result data
            ip_result = self.meta["result"].get(ip, empty_result)

            # empty jump
            if not ip_result:
                continue

            # finish
            if "finish" in kwargs:
                if kwargs["finish"] and not ip_result["f_time"]:
                    continue
                if not kwargs["finish"] and ip_result["f_time"]:
                    continue

            # success
            if "success" in kwargs:
                if kwargs["success"] and ip_result["status"] != TASK_STATUS_SUCCESS:
                    continue
                if not kwargs["success"] and ip_result["status"] == TASK_STATUS_SUCCESS:
                    continue

            # failure
            if "failure" in kwargs:
                if kwargs["failure"] and ip_result["status"] != TASK_STATUS_FAILURE:
                    continue
                if not kwargs["failure"] and ip_result["status"] == TASK_STATUS_FAILURE:
                    continue

            # time cost
            if "cost_gt" in kwargs:
                if ip_result["f_time"] - ip_result["c_time"] < kwargs["cost_gt"]:
                    continue
            if "cost_lt" in kwargs:
                if ip_result["f_time"] - ip_result["c_time"] > kwargs["cost_lt"]:
                    continue

            # code
            if "code" in kwargs:
                if ip_result["code"] != kwargs["code"]:
                    continue

            # retry
            # if "retry" in kwargs:
            #     if "retry"

            result["count"] += 1
            result["ips"].append(ip)
            result["details"][ip] = ip_result

        return result

    async def redo_task(self, target_hosts_filter=None, *, runner):
        # operation = await self.orm_operation.only_or_raise(id == self.meta["operation_id"],
        #                                                    columns=[orm.t.optn.id])
        target_hosts_filter = target_hosts_filter or {}
        if target_hosts_filter:
            target_hosts = (await self.parse_task_result(id=self.meta["id"],
                                                         **target_hosts_filter))["ips"]
        else:
            target_hosts = self.meta["hosts"]

        hf = host_filter.HostFilter({"id": None, "filters": [{"ip": {"in": target_hosts}}]})
        hosts = await hf.get_hosts(columns=[orm.t.h.ip, orm.t.h.envs])
        task_meta = dict(
            id=uuid.uuid4().hex,
            operation_id=self.meta["operation_id"],
            group_id=self.meta["group_id"],
            hosts=target_hosts,
            workflow=self.meta["workflow"],
            operator_id=self.meta["operator_id"],
            running_kwargs=self.meta["running_kwargs"],
            runner=runner.name,
            status={"task_status": TASK_STATUS_WAIT},
            result={},
        )
        logger.debug(task_meta)
        task_id = await self.orm.create(**task_meta)
        task = await self.orm.only_or_raise(orm.t.tsk.id == task_id)
        await main_mq.push_task_to_queue({**task, "hosts": hosts})
        await self.orm.query_update(orm.t.tsk.id == task_id,
                                    status={"task_status": TASK_STATUS_QUEUE})
        task = await self.orm.only_or_raise(orm.t.tsk.id == task_id)
        return task

    async def code_map(self):
        result = collections.defaultdict(lambda: 0)

        for ip in self.meta['hosts']:
            ip_code = self.meta["result"].get(ip, {}).get("code", None)
            code = ip_code if ip_code is not None else TASK_RETURN_CODE_UNKNOWN
            result[code] += 1

        return result
