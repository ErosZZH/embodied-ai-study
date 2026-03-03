#!/usr/bin/env python3
"""Execute commands on the remote GPU server via SSH."""
import sys
import os
import paramiko
import time
from dotenv import load_dotenv

load_dotenv()

HOST = "117.50.171.225"
USER = "ubuntu"
PASSWORD = os.getenv("VM_PASSWORD", "")


def run(cmd, timeout=300, stream=True):
    """Run a command on the remote server, streaming output."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)

    output = []
    if stream:
        for line in stdout:
            line = line.rstrip('\n')
            print(line)
            output.append(line)
    else:
        out = stdout.read().decode()
        print(out)
        output.append(out)

    exit_code = stdout.channel.recv_exit_status()

    err = stderr.read().decode().strip()
    if err and exit_code != 0:
        print(f"STDERR: {err}", file=sys.stderr)

    client.close()
    return exit_code


def copy_ssh_key():
    """Copy local SSH public key to remote server for future key-based auth."""
    import os
    pub_key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
    with open(pub_key_path) as f:
        pub_key = f.read().strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    cmd = f'mkdir -p ~/.ssh && echo "{pub_key}" >> ~/.ssh/authorized_keys && sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    client.close()
    print("SSH key copied successfully")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: remote_exec.py <command>")
        print("       remote_exec.py --copy-key")
        sys.exit(1)

    if sys.argv[1] == "--copy-key":
        copy_ssh_key()
    else:
        cmd = " ".join(sys.argv[1:])
        exit_code = run(cmd)
        sys.exit(exit_code)
