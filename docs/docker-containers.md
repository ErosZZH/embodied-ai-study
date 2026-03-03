# Docker Containers on the Remote Server

The remote GPU server runs **two Docker containers** for different purposes.

```
┌─────────────────────────────────────────────────────────────┐
│  Host: ubuntu@117.50.171.225  (RTX 4090, Ubuntu 22.04)     │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐    │
│  │  isaac-sim           │    │  isaac-lab               │    │
│  │  (Simulator + GUI)   │    │  (RL Training)           │    │
│  │                      │    │                          │    │
│  │  Isaac Sim 5.1.0     │    │  Isaac Sim 5.1 +         │    │
│  │  WebRTC Streaming    │    │  Isaac Lab 0.54.2 +      │    │
│  │  Port 8011 + 49100   │    │  rsl_rl + PyTorch        │    │
│  │                      │    │                          │    │
│  │  No RL libraries     │    │  No streaming server     │    │
│  └─────────────────────┘    └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Container Details

| | `isaac-sim` | `isaac-lab` |
|---|---|---|
| **Image** | `nvcr.io/nvidia/isaac-sim:5.1.0` | `nvcr.io/nvidia/isaac-lab:2.3.2` |
| **Purpose** | Simulator runtime + WebRTC livestream GUI | RL training (PPO, etc.) |
| **Contains** | Isaac Sim, rendering engine, physics engine, streaming server | Isaac Sim + Isaac Lab + rsl_rl + PyTorch + RL tooling |
| **Runs** | `./runheadless.sh` → streaming app on port 8011 | Idle container, we `docker exec` commands into it |
| **Origin** | Pre-installed by GPU rental provider (CompShare) | Created manually for this project |
| **Network** | `host` mode (ports 8011, 49100 exposed) | `host` mode |
| **Volume** | Caches + logs in `~/docker/isaac-sim/` | `~/isaac-lab-data/logs` → `/workspace/isaaclab/logs` |

## Why Two Containers?

**`isaac-sim`** came pre-installed with the GPU rental image. It runs Isaac Sim as a headless livestream server — you connect to it with the [Isaac Sim WebRTC Streaming Client](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/installation/download.html) to get a full 3D GUI. However, it does **not** have Isaac Lab or any RL libraries.

**`isaac-lab`** is what we set up for training. The `isaac-lab:2.3.2` Docker image bundles Isaac Sim + Isaac Lab + `rsl_rl` + PyTorch + everything needed for RL. All training happens here. It doesn't run a streaming server.

They share the same GPU but run independently. Training in `isaac-lab` does not show up in the `isaac-sim` viewport.

## Managing the Containers

```bash
# Check status of both containers
sudo docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

# Start / stop
sudo docker start isaac-sim
sudo docker stop isaac-sim
sudo docker start isaac-lab
sudo docker stop isaac-lab

# Execute commands inside isaac-lab (where training happens)
sudo docker exec isaac-lab bash -c '<command>'

# Interactive shell inside isaac-lab
sudo docker exec -it isaac-lab bash

# View logs
sudo docker logs isaac-sim    # streaming server logs
sudo docker logs isaac-lab    # container startup logs
```

## isaac-sim Container

### What It Does

Runs Isaac Sim in headless mode with WebRTC livestream enabled. This is the app you connect to with the streaming client to see a 3D viewport.

### How It Was Started

Defined in `/home/ubuntu/docker-compose.yml`:

```yaml
services:
  isaac-sim:
    image: nvcr.io/nvidia/isaac-sim:5.1.0
    container_name: isaac-sim
    network_mode: host
    environment:
      ACCEPT_EULA: "Y"
      PUBLIC_IP: ${PUBLIC_IP}
    volumes:
      - /home/ubuntu/docker/isaac-sim/cache/main:/isaac-sim/.cache
      - /home/ubuntu/docker/isaac-sim/cache/computecache:/isaac-sim/.nv/ComputeCache
      - /home/ubuntu/docker/isaac-sim/logs:/isaac-sim/.nvidia-omniverse/logs
      - /home/ubuntu/docker/isaac-sim/config:/isaac-sim/.nvidia-omniverse/config
      - /home/ubuntu/docker/isaac-sim/data:/isaac-sim/.local/share/ov/data
      - /home/ubuntu/docker/isaac-sim/pkg:/isaac-sim/.local/share/ov/pkg
    command: ["./runheadless.sh", "-v", "--/app/livestream/publicEndpointAddress=${PUBLIC_IP}"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

### Connecting to the Livestream

1. Download the [Isaac Sim WebRTC Streaming Client v1.0.6](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/installation/download.html) for your platform
2. Enter server address: `117.50.171.225`
3. The default streaming port is `8011`

**Note**: The livestream shows whatever scene is loaded in this container. By default it's an empty scene — it does **not** show training from the `isaac-lab` container.

### Key Paths Inside

```
/isaac-sim/                     ← Isaac Sim installation root
/isaac-sim/runheadless.sh       ← Starts headless streaming
/isaac-sim/python.sh            ← Python with Isaac Sim packages
/isaac-sim/apps/                ← Kit application configs
/isaac-sim/extension_examples/  ← Built-in examples (quadruped, etc.)
```

## isaac-lab Container

### What It Does

Provides the complete RL training environment. We `docker exec` training commands into it.

### How It Was Created

```bash
sudo docker run -d --name isaac-lab \
  --gpus all \
  --network host \
  -e ACCEPT_EULA=Y \
  -e PRIVACY_CONSENT=Y \
  -v /home/ubuntu/isaac-lab-data/logs:/workspace/isaaclab/logs:rw \
  nvcr.io/nvidia/isaac-lab:2.3.2
```

### Key Paths Inside

```
/workspace/isaaclab/                    ← Isaac Lab root
/workspace/isaaclab/isaaclab.sh         ← Entry point (wraps Python with Isaac Sim)
/workspace/isaaclab/scripts/            ← Training and evaluation scripts
  reinforcement_learning/rsl_rl/
    train.py                            ← PPO training script
    play.py                             ← Evaluation + video recording
/workspace/isaaclab/source/             ← Isaac Lab source code
  isaaclab_tasks/.../locomotion/velocity/
    velocity_env_cfg.py                 ← Base env config (rewards, observations, etc.)
    config/anymal_d/
      flat_env_cfg.py                   ← ANYmal-D flat terrain overrides
      rough_env_cfg.py                  ← ANYmal-D rough terrain config
      agents/rsl_rl_ppo_cfg.py          ← PPO hyperparameters
/workspace/isaaclab/logs/               ← Training output (mounted to host)
/workspace/isaaclab/_isaac_sim/         ← Bundled Isaac Sim runtime
```

### Versions

| Package | Version |
|---------|---------|
| Isaac Lab | 0.54.2 |
| Isaac Sim | 5.1.0 (bundled) |
| Python | 3.11.13 |
| PyTorch | 2.7.0 + CUDA 12.8 |
| rsl_rl | pre-installed |

## Monitoring Training

Since the two containers are independent, training in `isaac-lab` doesn't appear in the `isaac-sim` livestream. To monitor training:

### TensorBoard (recommended)

```bash
# From your local machine — starts TensorBoard and creates SSH tunnel in one command:
ssh -L 6006:localhost:6006 ubuntu@117.50.171.225 \
  "sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && tensorboard --logdir logs --bind_all --port 6006'"

# Then open http://localhost:6006 in your browser
```

### Terminal Output

Training prints reward/episode-length every iteration directly to the terminal:

```bash
ssh ubuntu@117.50.171.225 "sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py --task Isaac-Velocity-Flat-Anymal-D-v0 --num_envs 4096 --headless'"
```

### Post-Training Video

```bash
sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py --task Isaac-Velocity-Flat-Anymal-D-Play-v0 --num_envs 32 --load_run <run_name> --headless --video --enable_cameras'
```
