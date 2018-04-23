from op_center.server.worker_master import WorkerMaster

worker_master = WorkerMaster()

if __name__ == '__main__':
    worker_master.run_forever()