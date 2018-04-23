import celery

from op_center.basic import cfg, CELERY_TASK_NAME
from op_center.worker.celery_redis_worker import do_task

app = celery.Celery(broker=cfg["worker"]["celery"]["broker"],
                    backend=cfg["worker"]["celery"]["backend"])

app.task(name=CELERY_TASK_NAME)(do_task)

if __name__ == '__main__':
    app.worker_main()
