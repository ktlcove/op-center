from op_center.basic import Now, TASK_RETURN_CODE_CONNECTION_ERROR
from op_center.worker.ssh import SshWorker, SshWorkerConnectFailure
from op_center.worker.worker import ABCWorker


class CeleryWorker(ABCWorker, SshWorker):

    def __init__(self, workflow, host, running_kwargs, *, task_id):
        ABCWorker.__init__(self, workflow, host, running_kwargs,
                           task_id=task_id)
        SshWorker.__init__(self, host["ip"], ssh_info={"key_file": self.SSH_KEY_FILE})

    def run_run_shell(self, retry=0, **kwargs):
        result = self.exec_command_in_session(**kwargs, env=self.wf_envs)
        r = {"code": result[0],
             "stdout": result[1],
             "stderr": result[2],
             "desc": f"cmd: {kwargs['cmd']}",
             "timestamp": Now().timestamp()}
        if result[0] != 0:
            for i in range(retry):
                # self.update_history(self.mk_step_result(**r, retry=i + 1))
                result = self.exec_command_in_session(**kwargs, env=self.wf_envs)
                r = {"code": result[0],
                     "stdout": result[1],
                     "stderr": result[2],
                     "desc": f"cmd: {kwargs['cmd']}",
                     "retry": i + 1,
                     "timestamp": Now().timestamp()}
                if result[0] == 0:
                    break
        return r

    def run_scp(self, retry=0, **kwargs):
        result = self.scp_in_session(**kwargs)
        r = {"code": result[0],
             "stdout": result[1],
             "stderr": result[2],
             "desc": f"scp: {kwargs['source']} -> {kwargs['dist']}",
             "timestamp": Now().timestamp()}
        if result[0] != 0:
            for i in range(retry):
                # self.update_history(self.mk_step_result(**r, retry=i + 1))
                result = self.scp_in_session(**kwargs)
                r = {"code": result[0],
                     "stdout": result[1],
                     "stderr": result[2],
                     "desc": f"scp: {kwargs['source']} -> {kwargs['dist']}",
                     "retry": i + 1,
                     "timestamp": Now().timestamp()}
                if result[0] == 0:
                    break
        return r

    def _require_sftp_session(self):
        for w in self.wf_works:
            if w[0] == "scp":
                return True
        return False

    def work_init(self):
        if not ABCWorker.work_init(self):
            return False
        try:
            self.get_session()
            if self._require_sftp_session():
                self.get_sftp_session()
        except SshWorkerConnectFailure as e:
            self.update_history(self.mk_step_result(code=TASK_RETURN_CODE_CONNECTION_ERROR,
                                                    stderr=f"{e.__class__.__name__}: {str(e)}"))
            return False
        return True

    def work_done(self, result=None):
        if self._client:
            self._client.close()
        ABCWorker.work_done(self, result=result)


def do_task(*, workflow: dict, host: dict, running_kwargs: dict, task_id):
    celery_worker = CeleryWorker(workflow, host, running_kwargs, task_id=task_id)
    try:
        return celery_worker.do()
    except Exception as e:
        celery_worker.work_raise(e)
