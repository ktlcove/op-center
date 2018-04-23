import abc
import json

from op_center.basic import cfg, TASK_STATUS_SUCCESS, Now, TASK_STATUS_FAILURE, TASK_STATUS_ROUTER, \
    TASK_STATUS_RUNNING, \
    TASK_STATUS_FINISH, TASK_RETURN_CODE_SYSTEM_ERROR, TASK_RETURN_CODE_UNKNOWN_ERROR
from op_center.worker.mq import WorkerMQ
from op_center.workflow import WorkflowManager


class ABCWorker(metaclass=abc.ABCMeta):
    WORKFLOW_MANAGER = WorkflowManager()

    def __init__(self, workflow, host, running_kwargs, *, task_id):
        self.workflow_mata = workflow
        self.host = host
        self.running_kwargs = running_kwargs
        self.task_id = task_id
        self.worker_mq = WorkerMQ(link_kwargs=cfg["mq"]["main"])
        self._result = {
            "ip": self.host["ip"],
            "status": TASK_STATUS_RUNNING,
            "c_time": None,
            "f_time": None,
            "worker": None,
            "history": [],
            "code": None,
            "stdout": None,
            "stderr": None,
        }
        self.wf_works = None
        self.wf_envs = None
        self.wf_control = None

    def update_result(self, **kwargs):
        self._result.update(kwargs)
        self.worker_mq.write_host_result(self.task_id, self.host["ip"],
                                         json.dumps(self._result))

    def update_history(self, r, *rs):
        self._result["history"].extend([r, *rs])
        self.update_result()

    @staticmethod
    def mk_step_result(*code: int, **kwargs):
        d = {
            "code": code,
            "stdout": "",
            "stderr": "",
        }
        d.update(kwargs)
        return d

    def do(self):
        success = self.work_init()
        if success:
            for work in self.wf_works:
                try:
                    result = getattr(self, "run_" + work[0])(**work[1])
                except Exception as e:
                    result = self.mk_step_result(code=TASK_RETURN_CODE_SYSTEM_ERROR,
                                                 stderr=f"{e.__class__.__name__}: {e.args}")
                    success = False
                self.update_history(result)
                if result["code"] != 0:
                    success = False
                    break
        if not success:
            self.set_status_failure()
        else:
            self.set_status_success()
        self.work_done()

    def change_workflow_to_works(self):
        """
        work_envs = {
            ARGS_XXX: xxx
            ...
        }
        works = [
            (run_shell, {})
            (scp, {})
            ...
        ]
        """
        result = self.WORKFLOW_MANAGER.convert_workflow(self.workflow_mata, self.host, self.running_kwargs)
        self.wf_envs = result["envs"]
        self.wf_works = result["works"]
        self.wf_control = {}

    def set_status_success(self):
        self.worker_mq.change_task_status(self.task_id,
                                          {
                                              TASK_STATUS_SUCCESS + "__inc": 1,
                                          })

    def set_status_failure(self):
        self.worker_mq.change_task_status(self.task_id,
                                          {
                                              TASK_STATUS_FAILURE + "__inc": 1,
                                          })

    def work_init(self) -> bool:
        self.worker_mq.change_task_status(self.task_id,
                                          {
                                              TASK_STATUS_ROUTER + "__inc": -1,
                                              TASK_STATUS_RUNNING + "__inc": 1,
                                          })
        self.update_result(c_time=Now().timestamp(), status=TASK_STATUS_RUNNING)
        self.change_workflow_to_works()
        return True

    def work_done(self, result=None):
        """
        self._result = {
            "ip": self.host["ip"],
            "c_time": Now().timestamp(),
            "f_time": None,
            "worker": None,
            "history": self._history,
            "code": -3000,
            "stdout": None,
            "stderr": None,
        }
        :return:
        """
        if not result:
            if self._result["history"]:
                result = {
                    "code": self._result["history"][-1]["code"],
                    "stdout": "".join([h.get("stdout", "") for h in self._result['history']]),
                    "stderr": "".join([h.get("stderr", "") for h in self._result['history']]),
                }
            else:
                result = {"code": 0}
        if result["code"] == 0:
            status = TASK_STATUS_SUCCESS
        else:
            status = TASK_STATUS_FAILURE
        self.update_result(f_time=Now().timestamp(), status=status, **result)
        self.worker_mq.change_task_status(self.task_id,
                                          {
                                              TASK_STATUS_FINISH + "__inc": 1,
                                              TASK_STATUS_RUNNING + "__inc": -1,
                                          })
        self.worker_mq.close()

    def work_raise(self, e: Exception):
        self.work_done(result={"stderr": f"{type(e)}: {str(e)}",
                               "code": TASK_RETURN_CODE_UNKNOWN_ERROR})

    @abc.abstractmethod
    def run_run_shell(self, **kwargs):
        pass

    @abc.abstractmethod
    def run_scp(self, **kwargs):
        pass
