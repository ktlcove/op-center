import logging
import unittest

from op_center import workflow

logger = logging.getLogger(__name__)


class TestWorkflow(unittest.TestCase):

    def setUp(self):
        pass

    def test_step_run_shell(self):
        step = workflow.RunShellStep(dict(cmd="/path/to/test/cmd"))
        with self.assertRaises(workflow.StepException):
            step.operation_server()
        r_result = step.operation_remote()
        logger.info(r_result)
        self.assertIsInstance(r_result, tuple)

    def test_step_scp(self):
        step = workflow.ScpStep(dict(source="/path/to/test/source",
                                     dist="/path/to/test/dist"))
        with self.assertRaises(workflow.StepException):
            step.operation_server()
        r_result = step.operation_remote()
        logger.info(r_result)
        self.assertIsInstance(r_result, tuple)

    def test_workflow_remote(self):
        meta = {
            'id': 1,
            'args': {},
            'envs': {'LANG': 'en_US.UTF-8'},
            'name': 'test',
            'type': 'remote',
            'basic': {'creator': 'local-admin', 'timeout': 90},
            'steps': [{"run_shell": dict(cmd="/path/to/test/cmd"), },
                      {"scp": dict(source="/path/to/test/source",
                                   dist="/path/to/test/dist")}],
            'description': 'none'
        }
        host = {"ip": "test", "envs": {}}
        wf = workflow.RemoteWorkflow(meta=meta)
        works = wf.mk_work(host=host)
        logger.info(works)
        envs = wf.mk_env(host=host)
        logger.info(envs)

    def test_workflow_manager(self):
        meta = {
            'id': 1,
            'args': {},
            'envs': {'LANG': 'en_US.UTF-8'},
            'name': 'test',
            'type': 'remote',
            'basic': {'creator': 'local-admin', 'timeout': 90},
            'steps': [{"run_shell": dict(cmd="/path/to/test/cmd"), },
                      {"scp": dict(source="/path/to/test/source",
                                   dist="/path/to/test/dist")}],
            'description': 'none'
        }
        host = {"ip": "test", "envs": {}}
        wfm = workflow.WorkflowManager()
        result = wfm.convert_workflow(meta, host=host)
        logger.info(result)


if __name__ == '__main__':
    unittest.main()
