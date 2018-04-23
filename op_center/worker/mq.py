import re

from op_center.mq.redis_sync_mq import ABCSyncRedisOneLinkMQ


class WorkerMQ(ABCSyncRedisOneLinkMQ):
    TASK_INFO_PREFIX = "tasK_info_"
    TASK_QUEUE_KEY = "task_queue"
    TASK_STATUS_PREFIX = "task_status_"

    RUNNING_TASKS_KEY = "running_tasks"

    TASK_RESULT_PREFIX = "task_result_"

    MAX_RUNNING_TASKS_KEY = "max_running_tasks"
    MAX_QUEUE_TASKS_KEY = "max_queue_tasks"

    TASK_STATUS_KEY_SPLIT = re.compile(r"^(?P<field>.+)__(?P<action>[^_].+)$")

    def write_host_result(self, task_id, host_ip, result):
        key = self.TASK_RESULT_PREFIX + task_id
        self.conn.hset(key, host_ip, result)

    def change_task_status(self, task_id, status_map: dict):
        """
        task_status_task_id = {
        "total": int,
        "finish": int,
        "task_status": ...,
        KEYWORDS.TASK_STATUS_WAIT: int,
        KEYWORDS.TASK_STATUS_QUEUE: int,
        ...: ...
        """
        key = self.TASK_STATUS_PREFIX + task_id
        for k, v in status_map.items():
            tmp = self.TASK_STATUS_KEY_SPLIT.match(k)
            if tmp:
                field = tmp.groupdict().get("field")
                action = tmp.groupdict().get("action")
            else:
                field = k
                action = None
            if not action:
                self.conn.hset(key, field, v)
            else:
                if action == "inc":
                    self.conn.hincrby(key, field, v)
                else:
                    raise RuntimeError(f"action {action} error")

    def init_mq_conn(self):
        pass
