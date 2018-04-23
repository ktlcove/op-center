import uuid

from op_center.basic import TASK_STATUS_WAIT, TASK_STATUS_QUEUE
from op_center.server import orm
from op_center.server.host_filter import HostFilter
from op_center.server.mq import main_mq


class Operation(orm.OrmObject):

    @property
    def _orm_host_filter(self):
        if not self.__orm_host_filter:
            self.__orm_host_filter = orm.HostFilter(session=self.orm_session)
        return self.__orm_host_filter

    @property
    def _orm_operation(self):
        if not self.__orm_operation:
            self.__orm_operation = orm.Operation(session=self.orm_session)
        return self.__orm_operation

    @property
    def _orm_host(self):
        if not self.__orm_host:
            self.__orm_host = orm.Host(session=self.orm_session)
        return self.__orm_host

    @property
    def _orm_task(self):
        if not self.__orm_task:
            self.__orm_task = orm.Task(session=self.orm_session)
        return self.__orm_task

    @property
    def _orm_workflow(self):
        if not self.__orm_workflow:
            self.__orm_workflow = orm.WorkFlow(session=self.orm_session)
        return self.__orm_workflow

    async def get_host_filter(self):
        if not self._host_filter:
            meta = await self._orm_host_filter.only_or_raise(orm.t.hf.id == self.meta["host_filter_id"])
            self._host_filter = HostFilter(meta)
        return self._host_filter

    @classmethod
    async def create_by_id_or_name(cls, *, id=None, name=None,
                                   loop=None, user, orm_session=None, use_cache=False):
        if id:
            orm_session = orm_session or orm.DBSession()
            meta = await orm.Operation(session=orm_session).only_or_raise(orm.t.optn.id == id)
        elif name:
            orm_session = orm_session or orm.DBSession()
            meta = await orm.Operation(session=orm_session).only_or_raise(orm.t.optn.name == name)
        else:
            raise RuntimeError()
        return cls(meta, user, loop=loop, orm_session=orm_session, use_cache=use_cache)

    def __init__(self, meta, user, loop=None, orm_session=None, use_cache=False):
        super().__init__(meta, loop=loop, orm_session=orm_session)
        self.user = user
        self.use_cache = use_cache

        # orm 模型
        self.__orm_host_filter = None
        self.__orm_host = None
        self.__orm_operation = None
        self.__orm_workflow = None
        self.__orm_task = None

        # HostFilter 实例
        self._host_filter = None

        # 主机列表
        self._hosts = None
        self._host_ips = None

    async def run(self, running_kwargs: dict = None, hosts=None):
        workflow = await self.get_workflow(use_cache=self.use_cache)
        running_kwargs = running_kwargs or {}
        running_kwargs = {**workflow["args"], **running_kwargs}
        await self.get_hosts(use_cache=self.use_cache)
        task_meta = dict(
            id=uuid.uuid4().hex,
            operation_id=self.meta["id"],
            group_id=self.meta["group_id"],
            hosts=self._host_ips if hosts is None else hosts,
            workflow=workflow,
            operator_id=self.meta["operator_id"],
            running_kwargs=running_kwargs,
            runner=self.user.name,
            status={"task_status": TASK_STATUS_WAIT},
            result={},
        )
        task_id = await self._orm_task.create(**task_meta)
        task = await self._orm_task.only_or_raise(orm.t.tsk.id == task_id)
        await main_mq.push_task_to_queue({**task, "hosts": self._hosts})
        await self._orm_task.query_update(orm.t.tsk.id == task_id,
                                          status={"task_status": TASK_STATUS_QUEUE})
        task = await self._orm_task.only_or_raise(orm.t.tsk.id == task_id)
        return task

    async def get_hosts(self, use_cache=None):
        if not self._hosts:
            if use_cache:
                self._host_ips = self.meta["cache"]["hosts"]
                self._hosts = await self._orm_host.query(orm.t.h.ip.in_(self._host_ips),
                                                         columns=[orm.t.h.ip, orm.t.h.envs])
            else:
                host_filter = await self.get_host_filter()
                self._hosts = await host_filter.get_hosts(columns=[orm.t.h.ip, orm.t.h.envs])
                self._host_ips = [h["ip"] for h in self._hosts]
        return self._hosts

    async def get_workflow(self, use_cache=None):
        if use_cache:
            return self.meta["cache"]["workflow"]
        else:
            workflow = await self._orm_workflow.only_or_raise(orm.t.wf.id == self.meta["workflow_id"],
                                                              columns=[orm.t.wf.id, orm.t.wf.name,
                                                                       orm.t.wf.basic, orm.t.wf.description,
                                                                       orm.t.wf.type, orm.t.wf.steps,
                                                                       orm.t.wf.envs, orm.t.wf.args])
            return workflow

    async def refresh_cache(self):
        cache = {
            "hosts": [h["ip"] for h in await self.get_hosts(use_cache=False)],
            "workflow": await self.get_workflow(use_cache=False),
        }

        await self._orm_operation.query_update(orm.t.optn.id == self.meta["id"], cache=cache)
        self._meta = await self._orm_operation.only_or_raise(orm.t.optn.id == self.meta["id"])
