import paramiko
import json
import os
from dotenv import load_dotenv

load_dotenv()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('117.50.171.225', username='ubuntu', password=os.getenv('VM_PASSWORD', ''))

commands = [
    # 1. Check if Isaac Lab is partially installed
    ("1a. Find isaaclab/IsaacLab directories",
     "sudo docker exec isaac-sim find / -maxdepth 5 -name 'isaaclab' -o -name 'IsaacLab' 2>/dev/null"),
    ("1b. pip list grep isaac",
     "sudo docker exec isaac-sim pip list 2>/dev/null | grep -i isaac"),
    ("1c. Isaac Sim python pip list (isaac/rsl/rl_games/gymnasium/stable)",
     "sudo docker exec isaac-sim /isaac-sim/python.sh -m pip list 2>/dev/null | grep -i -E 'isaac|rsl|rl_games|gymnasium|stable'"),

    # 2. Disk space and volumes
    ("2a. df -h",
     "df -h"),
    ("2b. ls -la /home/ubuntu/",
     "ls -la /home/ubuntu/"),
    ("2c. Docker mounts",
     "sudo docker inspect isaac-sim --format='{{json .Mounts}}' | python3 -m json.tool"),

    # 3. Can we install packages inside the container?
    ("3. pip install --dry-run gymnasium",
     "sudo docker exec isaac-sim /isaac-sim/python.sh -m pip install --dry-run gymnasium 2>&1 | head -10"),

    # 4. Container writable state
    ("4a. Test write to /tmp",
     "sudo docker exec isaac-sim touch /tmp/test_write && echo 'writable' || echo 'read-only'"),
    ("4b. ls -la /isaac-sim/python.sh",
     "sudo docker exec isaac-sim ls -la /isaac-sim/python.sh"),

    # 5. Available Isaac Sim Python packages/modules
    ("5a. import isaacsim",
     "sudo docker exec isaac-sim /isaac-sim/python.sh -c \"import isaacsim; print(isaacsim.__path__)\" 2>&1"),
    ("5b. import omni.isaac.core",
     "sudo docker exec isaac-sim /isaac-sim/python.sh -c \"import omni.isaac.core; print('core ok')\" 2>&1"),

    # 6. Network connectivity from inside the container
    ("6. curl pypi.org from container",
     "sudo docker exec isaac-sim curl -s https://pypi.org/simple/ 2>&1 | head -3"),
]

for label, cmd in commands:
    print(f"\n{'='*70}")
    print(f">>> {label}")
    print(f"CMD: {cmd}")
    print('-'*70)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"STDOUT:\n{out}")
    if err.strip():
        print(f"STDERR:\n{err}")
    if not out.strip() and not err.strip():
        print("(no output)")

ssh.close()
print("\n\nDone.")
