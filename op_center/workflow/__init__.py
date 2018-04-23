import abc
import logging

from op_center.basic import WORKFLOW_TYPE_REMOTE, WORKFLOW_TYPE_SERVER, BasicException, Object

logger = logging.getLogger(__name__)

ALL_STEPS = {
    # name -> step_class
}


class WorkflowException(BasicException):
    pass


class StepException(WorkflowException):
    pass


class ABCStep(metaclass=abc.ABCMeta):
    NAME = None

    def __init__(self, meta: dict):
        self._meta = meta

    @property
    def meta(self):
        return self._meta

    @abc.abstractmethod
    def operation_server(self) -> ():
        pass

    @abc.abstractmethod
    def operation_remote(self) -> ():
        pass


def step_register(cls: ABCStep):
    if cls.NAME not in ALL_STEPS:
        logger.info(f"register step {cls.NAME}")
        ALL_STEPS[cls.NAME] = cls
    else:
        msg = f"step {cls.NAME} already in ALL_STEPS"
        logger.critical(msg)
        raise RuntimeError(msg)
    return cls


@step_register
class RunShellStep(ABCStep):
    """
        - run_shell:
            cmd: bash ...
            timeout: 30
            max_retry: 3
            auto_retry: true

    """
    NAME = "run_shell"

    def operation_remote(self):
        if "cmd" not in self.meta:
            raise StepException("run_shell need cmd input")
        result = (("run_shell", {"cmd": self.meta.get("cmd"),
                                 "timeout": self.meta.get("timeout", 300),
                                 "retry": self.meta.get("retry", 0),
                                 }
                   ),)
        logger.debug(f"{self.NAME}'s operation_remote is {result}")
        return result

    def operation_server(self):
        raise StepException("can't call this step in server workflow")


@step_register
class ScpStep(ABCStep):
    """
        - scp:
            remote: http://x.x.x.x/{host.basic.idc}.repo
            local: /etc/yum.repos.d/sample.repo
            max_retry: 3
            auto_retry: true
    """
    NAME = "scp"

    def operation_remote(self):
        if "source" not in self.meta or "dist" not in self.meta:
            raise StepException("source and dist must define")
        result = (("scp", {
            "source": self.meta.get("source"),
            "dist": self.meta.get("dist"),
            "retry": self.meta.get("retry", 0),
            "timeout": self.meta.get("timeout", 300),
            "md5": self.meta.get("md5", None),
        }),)
        logger.debug(f"{self.NAME}'s operation_remote is {result}")
        return result

    def operation_server(self):
        raise StepException("can't call this step in server workflow")


# @step_register
# class CurlStep(ABCStep):
#     """
#         - get_file:
#             remote: http://x.x.x.x/{host.basic.idc}.repo
#             local: /etc/yum.repos.d/sample.repo
#             max_retry: 3
#             auto_retry: true
#     """
#     NAME = "curl"
#     TEMPLATE = {
#         "source": str,
#         "dest": str,
#         "recurse": bool,
#     }
#
#     def __init__(self, source=None, dest=None, recurse=False):
#         self._meta = {
#             "source": source,
#             "dest": dest,
#             "recurse": recurse,
#         }
#
#     def to_shell(self, host_args: dict, running_args: dict) -> str:
#         pass
#
#
# @step_register
# class GitStep(ABCStep):
#     """
#         - get_file:
#             remote: http://x.x.x.x/{host.basic.idc}.repo
#             local: /etc/yum.repos.d/sample.repo
#             max_retry: 3
#             auto_retry: true
#     """
#     NAME = "git"
#     TEMPLATE = {
#         "source": str,
#         "dest": str,
#         "recurse": bool,
#     }
#
#     def __init__(self, source=None, dest=None, recurse=False):
#         self._meta = {
#             "source": source,
#             "dest": dest,
#             "recurse": recurse,
#         }
#
#     def to_shell(self, host_args: dict, running_args: dict) -> str:
#         pass
#

class ABCWorkflow(Object, metaclass=abc.ABCMeta):
    __steps__ = ALL_STEPS
    TYPE = None

    @property
    def name(self):
        return self.meta['name']

    @property
    def type(self):
        return self.meta['type']

    @property
    def envs(self):
        return self.meta["envs"]

    @property
    def basic(self):
        return self.meta["basic"]

    @property
    def steps(self):
        return self.meta["steps"]

    @abc.abstractmethod
    def mk_work(self, host: dict = None, running_kwargs: dict = None):
        pass

    @abc.abstractmethod
    def mk_env(self, host: dict = None, running_kwargs: dict = None):
        pass


class WorkflowManager:
    WORKFLOW = {}

    def __init__(self):
        pass

    def create_workflow(self, meta: dict) -> ABCWorkflow:
        if meta["type"] in self.WORKFLOW:
            return self.WORKFLOW[meta["type"]](meta)
        else:
            raise WorkflowException(f"unsupported type of workflow type is: {meta['type']}")

    def convert_workflow(self, meta: dict, host: dict = None, running_kwargs: dict = None):

        """
        :param meta:  {
                'id': 1,
                'args': {},
                'envs': {'LANG': 'en_US.UTF-8'},
                'name': 'test-http-view2',
                'type': 'remote',
                'basic': {'creator': 'local-admin', 'timeout': 90},
                'steps': [],
                'description': 'none'
                }
        :param host: {
                'ip': '10.0.0.64',
                'envs': {'ARGS_BASIC_IDC': 'idc1'}
                }
        :param running_kwargs: {
                'a': 'b',
                'foo': 'bar',
                }
        :return:
        """

        workflow = self.create_workflow(meta)
        works = workflow.mk_work(host=host, running_kwargs=running_kwargs)
        envs = workflow.mk_env(host=host, running_kwargs=running_kwargs)
        return {"works": works, "envs": envs}


def workflow_register(cls: ABCWorkflow):
    if cls.TYPE not in ALL_STEPS:
        logger.info(f"register workflow {cls.TYPE}")
        WorkflowManager.WORKFLOW[cls.TYPE] = cls
    else:
        msg = f"step {cls.TYPE} already in ALL_WORKFLOW"
        logger.error(msg)
        raise RuntimeError(msg)
    return cls


@workflow_register
class RemoteWorkflow(ABCWorkflow):
    TYPE = WORKFLOW_TYPE_REMOTE

    def mk_env(self, host: dict = None, running_kwargs: dict = None):
        if not host:
            raise WorkflowException("need host input")
        running_kwargs = running_kwargs or {}
        return {**self.envs, **host["envs"], **{k.upper(): v for k, v in running_kwargs.items()}}

    def mk_work(self, host: dict = None, running_kwargs: dict = None):
        works = []
        running_kwargs = running_kwargs or {}
        for step in self.steps:
            step_name, step_body = list(step.items())[0]
            step_obj = ALL_STEPS[step_name](step_body)
            step_works = step_obj.operation_remote()
            works.extend(step_works)
        logger.debug(f"convert to work: host is {host} running_kwargs is {running_kwargs}"
                     f"result is {works}")
        return works


@workflow_register
class ServerWorkflow(ABCWorkflow):
    TYPE = WORKFLOW_TYPE_SERVER

    def mk_env(self, host: dict = None, running_kwargs: dict = None):
        if not host:
            raise WorkflowException("need host input")
        running_kwargs = running_kwargs or {}
        return {**self.envs, **host["envs"], **{k.upper(): v for k, v in running_kwargs.items()}}

    def mk_work(self, host: dict = None, running_kwargs: dict = None):
        works = []
        running_kwargs = running_kwargs or {}
        for step in self.steps:
            step_name, step_body = list(step.items())[0]
            step_obj = ALL_STEPS[step_name](step_body)
            step_works = step_obj.operation_server()
            works.extend(step_works)
        logger.debug(f"convert to work: host is {host} running_kwargs is {running_kwargs}"
                     f"result is {works}")
        return works
