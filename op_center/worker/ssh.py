import hashlib
import io
import socket
import time

import paramiko

from op_center.basic import cfg, TASK_RETURN_CODE_SFTP_TRANSFER_TIMEOUT, TASK_RETURN_CODE_SSH_CMD_TIMEOUT, \
    TASK_RETURN_CODE_SFTP_TRANSFER_IO_ERROR


class SshException(Exception):
    pass


class _ParamikoSftpTransferTimeout(SshException):
    pass


class SshWorkerConnectFailure(SshException):
    pass


class SshWorker:
    SSH_CFG = cfg["worker"]["celery"]["ssh"]
    SSH_CONNECT_TIMEOUT = SSH_CFG["connect_timeout"]
    SSH_PORT = SSH_CFG["port"]
    SSH_USER = SSH_CFG["user"]
    SSH_KEY_FILE = SSH_CFG["key_file"]
    with open(SSH_KEY_FILE) as _f:
        SSH_KEY = paramiko.RSAKey.from_private_key(_f)

    def __init__(self, ip, *, ssh_info=None):
        self.ip = ip
        self.ssh_info = ssh_info or {}
        self._client = None
        self.read_timeout = 0.2

    def get_client(self):
        if not self._client:
            try:
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._client.connect(hostname=self.ip,
                                     port=self.ssh_info.get("port", self.SSH_PORT),
                                     username=self.ssh_info.get("user", self.SSH_USER),
                                     # key_filename=self.ssh_info.get("key_file", self.SSH_KEY_FILE),
                                     pkey=self.SSH_KEY,
                                     timeout=self.ssh_info.get("timeout", self.SSH_CONNECT_TIMEOUT),
                                     allow_agent=False)
            except Exception as e:
                self._client = None
                raise SshWorkerConnectFailure(f"{e.__class__.__name__} {str(e)}")
        return self._client

    def get_session(self, timeout=None):
        client = self.get_client()
        try:
            new_session = client.get_transport().open_session(timeout=timeout)
            new_session.settimeout(self.read_timeout)
            return new_session
        except BaseException as e:
            raise SshWorkerConnectFailure(f"{type(e)} {str(e)}")

    def get_sftp_session(self):
        client = self.get_client()
        try:
            sftp_session = paramiko.SFTPClient.from_transport(client.get_transport())
            return sftp_session
        except BaseException as e:
            raise SshWorkerConnectFailure(f"{type(e)} {str(e)}")

    def kill_my_client_all_process(self, *, timeout=3):
        client = self.get_client()
        l_ip, l_port = client.get_transport().sock.getsockname()
        r_ip, r_port = client.get_transport().sock.getpeername()
        cmd = f"""
        ARGS_SSH_PID=` \
        netstat -antlp | \
        grep "{l_ip}:{l_port}" | \
        grep "{r_ip}:{r_port}" | \
        awk -F"/" '{{print $1}}' | \
        awk '{{print $NF}}'`
        pids=`\
        ps -o pid,ppid -e -p $ARGS_SSH_PID | \
        grep $ARGS_SSH_PID | \
        awk '{{print $1}}' | \
        grep -v $ARGS_SSH_PID`
        for p in $pids ; do echo "kill $p" && kill -9 -$p ; done
        """
        self.exec_command_in_session(cmd, timeout=timeout)

    def get_remote_file_md5(self, remote_path, *, timeout):
        cmd = f"""
        test -e {remote_path} && ( md5sum {remote_path} | awk '{{print $1}}' )
        """
        result = self.exec_command_in_session(cmd, timeout=timeout)
        if result[0] == 0:
            return result[1].strip(" \n\t")
        else:
            return None

    def recv_session_output(self, session, *, timeout):
        start_time = time.time()
        stderr = io.BytesIO()
        stdout = io.BytesIO()
        exit_status = TASK_RETURN_CODE_SSH_CMD_TIMEOUT
        success = False
        while True:
            if session.exit_status_ready():
                exit_status = session.recv_exit_status()
                success = True
            try:
                data = session.recv(10240)
                while data:
                    stdout.write(data)
                    data = session.recv(10240)
            except socket.timeout:
                pass
            try:
                data = session.recv_stderr(10240)
                while data:
                    stderr.write(data)
                    data = session.recv_stderr(10240)
            except socket.timeout:
                pass
            if success:
                break
            if time.time() - start_time >= timeout:
                self.kill_my_client_all_process()
                break
            time.sleep(self.read_timeout)
        result = (exit_status,
                  stdout.getvalue().decode(errors="ignore"),
                  stderr.getvalue().decode(errors="ignore"))
        return result

    def exec_command_in_session(self, cmd, *, timeout, env=None):
        session = self.get_session()
        if env:
            env_cmds = [f"export {key}='{value}' " for key, value in env.items()]
            cmd = "\n".join([*env_cmds, cmd])
        session.exec_command(cmd)
        exit_status, stdout, stderr = self.recv_session_output(session, timeout=timeout)
        session.close()
        return exit_status, stdout, stderr

    def scp_in_session(self, source, dist, *, timeout, md5=None):
        sftp_session = self.get_sftp_session()
        start_time = time.time()
        remote_md5 = self.get_remote_file_md5(dist, timeout=timeout)

        if remote_md5 and remote_md5 == md5:
            return 0, "", ""

        local_file = io.BytesIO()
        try:
            with open(source, "rb") as _f:
                local_file.write(_f.read())
        except OSError as e:
            return -1002, "", f"read local file error: {str(e)}"
        local_file_length = local_file.tell()
        local_file.seek(0)
        if remote_md5:
            local_md5 = md5 or hashlib.md5(local_file.getvalue()).hexdigest()
            if local_md5 == remote_md5:
                return 0, "", ""

        def callback(already_finish, total_count):
            if time.time() - start_time > timeout:
                raise _ParamikoSftpTransferTimeout(f"timeout: transfer present is "
                                                   f"({already_finish/1048576:.2f}m/{total_count/1048576:.2f}m)"
                                                   f"[{already_finish/total_count*100:.2f}%]"
                                                   f"[{already_finish/timeout/1048576:.2f}mib/s].")

        try:
            sftp_session.putfo(local_file, dist, file_size=local_file_length,
                               callback=callback, confirm=True)
        except _ParamikoSftpTransferTimeout as e:
            sftp_session.close()
            return TASK_RETURN_CODE_SFTP_TRANSFER_TIMEOUT, "", str(e)
        except IOError as e:
            sftp_session.close()
            return TASK_RETURN_CODE_SFTP_TRANSFER_IO_ERROR, "", str(e)
        sftp_session.close()
        return 0, "", ""


if __name__ == '__main__':
    c = SshWorker("127.0.0.1")
    print(c.exec_command_in_session("echo a", timeout=1, env={"test": 1}))
