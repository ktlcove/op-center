import logging

from op_center.basic import PMS_CREATE_HOST_FILTER, PMS_MODIFY_HOST_FILTER, PMS_DELETE_HOST_FILTER, \
    WORKFLOW_TYPE_REMOTE, PMS_CREATE_WORKFLOW, PMS_MODIFY_WORKFLOW, PMS_SEARCH_WORKFLOW, PMS_DELETE_WORKFLOW, \
    PMS_SEARCH_HOST_FILTER, PMS_CREATE_OPERATOR, PMS_DELETE_OPERATOR, PMS_MODIFY_OPERATOR, PMS_SEARCH_OPERATOR, \
    PMS_CREATE_OPERATION, PMS_MODIFY_OPERATION, PMS_DELETE_OPERATION, PMS_SEARCH_TASK, PMS_RUN_OPERATION
from op_center.server import host_filter, user
from op_center.server import orm
from op_center.server.controller.exception import ControllerException
from op_center.server.controller.permission import pms_required, overall_pms_required, PermissionDeny
from op_center.server.mq import main_mq
from op_center.server.operation import Operation
from op_center.server.task import Task

logger = logging.getLogger(__name__)


class UnsupportedOperation(ControllerException):
    code = 400


class ArgumentError(ControllerException):
    code = 400


class Controller:
    mq = main_mq

    @property
    def orm_user(self):
        if not self._orm_user:
            self._orm_user = orm.User(session=self.orm_session)
        return self._orm_user

    @property
    def orm_host_filter(self):
        if not self._orm_host_filter:
            self._orm_host_filter = orm.HostFilter(session=self.orm_session)
        return self._orm_host_filter

    @property
    def orm_workflow(self):
        if not self._orm_workflow:
            self._orm_workflow = orm.WorkFlow(session=self.orm_session)
        return self._orm_workflow

    @property
    def orm_operator(self):
        if not self._orm_operator:
            self._orm_operator = orm.Operator(session=self.orm_session)
        return self._orm_operator

    @property
    def orm_operation(self):
        if not self._orm_operation:
            self._orm_operation = orm.Operation(session=self.orm_session)
        return self._orm_operation

    @property
    def orm_task(self):
        if not self._orm_task:
            self._orm_task = orm.Task(session=self.orm_session)
        return self._orm_task

    def __init__(self, u: user.User, loop=None, orm_session=None):
        self.orm_session = orm_session or orm.DBSession()
        self.loop = loop
        self.user = u

        self._orm_user = None
        self._orm_host_filter = None
        self._orm_workflow = None
        self._orm_operator = None
        self._orm_operation = None
        self._orm_task = None

    @staticmethod
    def mk_update_dict(*, _ignores=None, **kwargs):
        if _ignores is None:
            _ignores = [None]
        return {k: v for k, v in kwargs.items() if v not in _ignores}

    async def __fill_user_basic_group_id(self, group_id=None):
        return group_id or await self.user.my_basic_group_id()

    async def __get_workflow_group_id(self, *, id):
        return (await self.orm_workflow.only_or_raise(orm.t.wf.id == id))["group_id"]

    async def __get_host_filter_group_id(self, *, id):
        return (await self.orm_host_filter.only_or_raise(orm.t.hf.id == id))["group_id"]

    async def __get_operation_group_id(self, *, id):
        return (await self.orm_operation.only_or_raise(orm.t.optn.id == id))["group_id"]

    async def __get_task_group_id(self, *, id):
        return (await self.orm_task.only_or_raise(orm.t.tsk.id == id))["group_id"]

    # host filter
    @pms_required(PMS_CREATE_HOST_FILTER,
                  group_id_function=__fill_user_basic_group_id,
                  group_id_params={"group_id": "group_id"})
    async def create_host_filter(self, *, name, filters, description=None, group_id=None):
        if not filters:
            raise UnsupportedOperation("filters can't be empty")

        await self.orm_host_filter.not_exist_or_raise(orm.t.hf.name == name)
        meta = {
            "name": name,
            "description": description,
            "filters": filters,
            "group_id": group_id or await self.user.my_basic_group_id(),
        }
        await host_filter.HostFilter(meta).get_hosts()
        new_host_filter_id = await self.orm_host_filter.create(**meta)
        logger.debug(f"create host filter ok id is: {new_host_filter_id}")
        return await self.orm_host_filter.only_or_raise(orm.t.hf.id == new_host_filter_id)

    @pms_required(PMS_MODIFY_HOST_FILTER,
                  group_id_function=__get_host_filter_group_id,
                  group_id_params={"id": "id"})
    async def update_host_filter(self, id, name=None, filters=None, description=None):
        target = await self.orm_host_filter.only_or_raise(orm.t.hf.id == id)
        # 判断 如果是从共有改成私有则拒绝
        # if change group_id from null -> some_id deny
        # if target["group_id"] is None and group_id != target["group_id"]:
        #     raise UnsupportedOperation("can't change a group from public to private"
        #                                ", if you real wan't to do this try fork this to your self group")
        if filters is not None:
            if type(filters) is not list or filters == []:
                raise UnsupportedOperation("filters must be a not empty list")

        update_dict = self.mk_update_dict(name=name,
                                          filters=filters,
                                          description=description)
        meta = target
        meta.update(update_dict)
        await host_filter.HostFilter(meta).get_hosts()
        await self.orm_host_filter.query_update(orm.t.hf.id == id, **update_dict)

    @pms_required(PMS_SEARCH_HOST_FILTER,
                  group_id_function=__get_host_filter_group_id,
                  group_id_params={"id": "id"})
    @pms_required(PMS_CREATE_HOST_FILTER,
                  group_id_function=__fill_user_basic_group_id,
                  group_id_params={"group_id": "group_id"})
    async def fork_host_filter(self, id, name=None, group_id=None):
        """
        copy a host_filter to my group
        :param id: target id
        :param name: new host_filter name
        ":param group_id: copy to which group , default is user.basic_group
        """
        target = await self.orm_host_filter.only_or_raise(orm.t.hf.id == id)
        group_id = group_id or await self.user.my_basic_group_id()
        name = name or target["name"] + f" fork[{group_id}]"
        return await self.create_host_filter(name=name,
                                             filters=target["filters"],
                                             description=target["description"],
                                             group_id=group_id)

    @pms_required(PMS_SEARCH_HOST_FILTER,
                  group_id_function=__get_host_filter_group_id,
                  group_id_params={"id": "id"})
    async def get_host_filter_hosts(self, id):
        hf = await host_filter.HostFilter.create_by_name_or_id(id=id)
        return await hf.get_hosts(columns=[orm.t.h.ip, orm.t.h.envs])

    @pms_required(PMS_DELETE_HOST_FILTER,
                  group_id_function=__get_host_filter_group_id,
                  group_id_params={"id": "id"})
    async def delete_host_filter(self, id):
        #
        # put relate check here
        #
        await self.orm_host_filter.query_delete(orm.t.hf.id == id)

    async def get_host_filters(self, id=None):
        if id:
            return await self.orm_host_filter.query(orm.t.hf.id == id)
        else:
            return await self.orm_host_filter.query()

    # workflow
    @pms_required(PMS_CREATE_WORKFLOW,
                  group_id_function=__fill_user_basic_group_id,
                  group_id_params={"group_id": "group_id"})
    async def create_workflow(self, *, name, description=None,
                              steps=None, basic=None, envs=None, args=None,
                              type=WORKFLOW_TYPE_REMOTE, group_id=None):
        basic = basic or {}
        meta = {
            "name": name,
            "basic": {
                "creator": self.user.name,
                "timeout": basic.get("timeout", 90),
            },
            "type": type,
            "envs": envs or {},
            "steps": steps or [],
            "group_id": group_id or await self.user.my_basic_group_id(),
            "description": description,
            "args": args or {},
        }
        if "LANG" not in meta["envs"]:
            meta["envs"]["LANG"] = "en_US.UTF-8"
        meta_id = await self.orm_workflow.create(**meta)
        return await self.orm_workflow.only_or_raise(orm.t.wf.id == meta_id)

    @pms_required(PMS_MODIFY_WORKFLOW,
                  group_id_function=__get_workflow_group_id,
                  group_id_params={"id": "id"})
    async def update_workflow(self, id, name=None, description=None,
                              steps=None, basic=None, envs=None, args=None):
        update_dict = self.mk_update_dict(name=name, description=description, steps=steps,
                                          basic=basic, envs=envs, args=args)
        if not update_dict:
            return
        await self.orm_workflow.query_update(orm.t.wf.id == id, **update_dict)

    @pms_required(PMS_SEARCH_WORKFLOW,
                  group_id_function=__get_workflow_group_id,
                  group_id_params={"id": "id"})
    @pms_required(PMS_CREATE_WORKFLOW,
                  group_id_function=__fill_user_basic_group_id,
                  group_id_params={"group_id": "group_id"})
    async def fork_workflow(self, id, name=None, group_id=None):
        target = await self.orm_workflow.only_or_raise(orm.t.wf.id == id)
        group_id = group_id or await self.user.my_basic_group_id()
        name = name or target["name"] + f" fork[{group_id}]"
        return await self.create_workflow(name=name,
                                          description=target["description"],
                                          steps=target["steps"],
                                          basic=target["basic"],
                                          envs=target["envs"],
                                          args=target["args"],
                                          type=target["type"],
                                          group_id=group_id)

    @pms_required(PMS_DELETE_WORKFLOW,
                  group_id_function=__get_workflow_group_id,
                  group_id_params={"id": "id"})
    async def delete_workflow(self, id):
        return await self.orm_workflow.query_delete(orm.t.wf.id == id)

    async def get_workflow(self, id=None):
        if id:
            return await self.orm_workflow.query(orm.t.wf.id == id)
        else:
            return await self.orm_workflow.query()

    # operator
    @overall_pms_required(PMS_CREATE_OPERATOR)
    async def create_operator(self, *, name, description=None, type, mq_link=None):
        if not mq_link:
            raise ArgumentError("mq_link can't be empty")
        meta_id = await self.orm_operator.create(
            name=name,
            description=description,
            type=type,
            mq_link=mq_link
        )
        meta = await self.orm_operator.only_or_raise(orm.t.optr.id == meta_id)
        return meta

    @overall_pms_required(PMS_DELETE_OPERATOR)
    async def delete_operator(self, id):
        return await self.orm_operator.query_delete(orm.t.optr.id == id)

    @overall_pms_required(PMS_MODIFY_OPERATOR)
    async def update_operator(self, id, name=None, description=None, mq_link=None):
        await self.orm_operator.query_update(orm.t.optr.id == id,
                                             **self.mk_update_dict(name=name,
                                                                   description=description,
                                                                   mq_link=mq_link))

    @overall_pms_required(PMS_SEARCH_OPERATOR)
    async def get_operator(self, id=None):
        if id:
            return await self.orm_operator.query(orm.t.optr.id == id)
        else:
            return await self.orm_operator.query()

    # operation
    @pms_required(PMS_CREATE_OPERATION,
                  group_id_function=__fill_user_basic_group_id,
                  group_id_params={"group_id": "group_id"})
    async def create_operation(self, *, name, description=None, group_id=None,
                               workflow_id, operator_id=None, host_filter_id, auto_fork=True):
        # 尝试填充用户的目标分组
        group_id = group_id or await self.user.my_basic_group_id()
        # 检查目标operation是否重复
        await self.orm_operation.not_exist_or_raise(orm.t.optn.name == name,
                                                    orm.t.optn.group_id == group_id)

        # 检查 workflow host_filter 是否存在
        workflow = await self.orm_workflow.only_or_raise(orm.t.wf.id == workflow_id)
        hf = await self.orm_host_filter.only_or_raise(orm.t.hf.id == host_filter_id)

        # 如果使用非默认operator 检查是否存在
        if operator_id:
            await self.orm_operator.only_or_raise(orm.t.optr.id == operator_id)

        # 判断是否需要fork
        fork = set()
        if workflow["group_id"] and workflow["group_id"] != group_id:
            fork.add("workflow")
        if hf["group_id"] and hf["group_id"] != group_id:
            fork.add("host_filter")

        if fork:

            # 需要fork且未指定自动fork 报错
            if not auto_fork:
                raise UnsupportedOperation(f"{fork} is not in group<id={group_id}>, "
                                           f"fork it first or spec other instead it")

            # 检查是否有fork权限（查询即fork权限）
            if "workflow" in fork:
                if PMS_SEARCH_WORKFLOW not in \
                        await self.user.my_group_private_permissions(workflow["group_id"]):
                    raise PermissionDeny(f"you have no permission {PMS_SEARCH_WORKFLOW} "
                                         f"for workflow's group group<id={workflow['group_id']}>")
            if "host_filter" in fork:
                if PMS_SEARCH_HOST_FILTER not in \
                        await self.user.my_group_private_permissions(hf["group_id"]):
                    raise PermissionDeny(f"you have no permission {PMS_SEARCH_WORKFLOW} "
                                         f"for workflow's group group<id={hf['group_id']}>")

            # fork 出新资源 代替原有的资源备用
            workflow = await self.fork_workflow(id=workflow["id"], group_id=group_id)
            hf = await self.fork_host_filter(id=hf["id"], group_id=group_id)

        # 创建
        meta_id = await self.orm_operation.create(name=name,
                                                  description=description,
                                                  group_id=group_id,
                                                  workflow_id=workflow["id"],
                                                  host_filter_id=hf["id"],
                                                  operator_id=operator_id,
                                                  cache={})
        return await self.orm_operation.only_or_raise(orm.t.optn.id == meta_id)

    @pms_required(PMS_MODIFY_OPERATION,
                  group_id_function=__get_operation_group_id,
                  group_id_params={"id": "id"})
    async def update_operation(self, id, *, name=None, description=None,
                               workflow_id=None, operator_id=None, host_filter_id=None, auto_fork=False):
        pass

    @pms_required(PMS_MODIFY_OPERATION,
                  group_id_function=__get_operation_group_id,
                  group_id_params={"id": "id"})
    async def operation_refresh_cache(self, id):
        operation_instance = await Operation.create_by_id_or_name(id=id, user=self.user,
                                                                  orm_session=self.orm_session,
                                                                  use_cache=False)
        return await operation_instance.refresh_cache()

    async def get_operation(self, id=None):
        if id:
            return await self.orm_operation.query(orm.t.optn.id == id)
        else:
            return await self.orm_operation.query()

    @pms_required(PMS_DELETE_OPERATION,
                  group_id_function=__get_operation_group_id,
                  group_id_params={"id": "id"})
    async def delete_operation(self, id):
        return await self.orm_operation.query_delete(orm.t.optn.id == id)

    @pms_required(PMS_RUN_OPERATION,
                  group_id_function=__get_operation_group_id,
                  group_id_params={"id": "id"})
    async def operation_run(self, id, running_kwargs: dict = None, use_cache=True, hosts=None):
        operation_instance = await Operation.create_by_id_or_name(id=id, user=self.user,
                                                                  orm_session=self.orm_session,
                                                                  use_cache=use_cache)
        return await operation_instance.run(running_kwargs=running_kwargs, hosts=hosts)

    # task
    async def get_task(self, id=None):
        if id:
            return await self.orm_task.query(orm.t.tsk.id == id, columns=[orm.t.tsk.id,
                                                                          orm.t.tsk.operation_id,
                                                                          orm.t.tsk.group_id,
                                                                          orm.t.tsk.running_kwargs,
                                                                          orm.t.tsk.runner,
                                                                          orm.t.tsk.status,
                                                                          orm.t.tsk.c_time,
                                                                          orm.t.tsk.m_time,
                                                                          orm.t.tsk.f_time])
        else:
            return await self.orm_task.query(columns=[orm.t.tsk.id,
                                                      orm.t.tsk.operation_id,
                                                      orm.t.tsk.group_id,
                                                      orm.t.tsk.running_kwargs,
                                                      orm.t.tsk.runner,
                                                      orm.t.tsk.status,
                                                      orm.t.tsk.c_time,
                                                      orm.t.tsk.m_time,
                                                      orm.t.tsk.f_time])

    @pms_required(PMS_SEARCH_TASK,
                  group_id_function=__get_task_group_id,
                  group_id_params={"id": "id"})
    async def get_task_status(self, id):
        t = await Task.create_by_id(id, orm_session=self.orm_session)
        return t.meta["status"]

    @pms_required(PMS_SEARCH_TASK,
                  group_id_function=__get_task_group_id,
                  group_id_params={"id": "id"})
    async def get_task_result(self, id):
        t = await Task.create_by_id(id, orm_session=self.orm_session)
        return t.meta["result"]

    @pms_required(PMS_SEARCH_TASK,
                  group_id_function=__get_task_group_id,
                  group_id_params={"id": "id"})
    async def parse_task_result(self, id, **kwargs):
        t = await Task.create_by_id(id, orm_session=self.orm_session)
        return await t.parse_task_result(**kwargs)

    @pms_required(PMS_SEARCH_TASK,
                  group_id_function=__get_task_group_id,
                  group_id_params={"id": "id"})
    async def task_code_map(self, id):
        t = await Task.create_by_id(id, orm_session=self.orm_session)
        return await t.code_map()

    @pms_required(PMS_RUN_OPERATION,
                  group_id_function=__get_task_group_id,
                  group_id_params={"id": "id"})
    async def redo_task(self, id, target_hosts_filter=None):
        t = await Task.create_by_id(id, orm_session=self.orm_session)
        return await t.redo_task(target_hosts_filter=target_hosts_filter, runner=self.user)
