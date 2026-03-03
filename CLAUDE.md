# Embodied AI Study — Project Guide

## Project Goal

Train quadruped robots (machine dogs) to walk using reinforcement learning in NVIDIA Isaac Sim.

## Reference Material

- `docs/机器人入门学习计划.pdf` — 2-month, 5-sprint learning roadmap covering RL-based locomotion, AMP/Mimic, Sim2Real, whole-body control, and domain randomization.

## Remote GPU Server

- **Host**: `ubuntu@117.50.171.225`
- **GPU Rental**: https://console.compshare.cn/light-gpu/console/resources
- **Image**: Isaac Sim Webrtc Ubuntu 22.04

### Hardware

| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 4090 (24 GB VRAM) |
| CPU | AMD EPYC 7413, 16 vCPUs (8 cores, 2 threads/core) |
| RAM | 62 GB |
| Disk | 194 GB total (~153 GB free) |
| NVIDIA Driver | 575.57.08 |
| CUDA | 12.9 |

### Software (inside Docker container `isaac-sim`)

- **Isaac Sim**: 5.1.0 (`nvcr.io/nvidia/isaac-sim:5.1.0`)
- **Running mode**: Headless livestream via `./runheadless.sh` (app: `isaacsim.exp.full.streaming.kit`)
- **Livestream address**: `117.50.171.225:8011` (connect via NVIDIA Omniverse Streaming Client)
- **Python**: 3.11.13
- **PyTorch**: 2.7.0 + CUDA 12.8
- **Docker compose**: `/home/ubuntu/docker-compose.yml`

### Pre-installed Isaac Sim Extensions (key ones)

- `isaacsim.robot.policy.examples` — Pre-trained policies for **ANYmal**, **Spot**, **H1**, **Franka**
- `isaacsim.asset.importer.urdf` / `.mjcf` — Robot model importers
- `isaacsim.sensors.physics` — Contact sensors, IMU
- `isaacsim.replicator.domain_randomization` — Domain randomization
- `isaacsim.ros2.bridge` — ROS2 integration
- Quadruped example: `/isaac-sim/extension_examples/quadruped/`

### What is NOT installed (needs setup)

- **Isaac Lab** (main RL training framework for Isaac Sim 5.x, replaces legged_gym/IsaacGymEnvs/ORBIT)
- **RL libraries**: `rsl_rl`, `rl_games`, `stable-baselines3`, `gymnasium`
- **legged_gym** (older quadruped RL env)

## Useful Commands

```bash
# SSH into server
ssh ubuntu@117.50.171.225

# Execute commands inside Isaac Sim container
sudo docker exec isaac-sim <command>

# Run Python inside Isaac Sim container
sudo docker exec isaac-sim /isaac-sim/python.sh -c "print('hello')"

# Install pip packages inside container
sudo docker exec isaac-sim /isaac-sim/python.sh -m pip install <package>

# Check GPU status
ssh ubuntu@117.50.171.225 nvidia-smi

# View Isaac Sim container logs
ssh ubuntu@117.50.171.225 sudo docker logs isaac-sim
```

## Training Plan Overview

### Phase 0 — Environment Setup
Install Isaac Lab + RL dependencies inside the Docker container.

### Phase 1 — Basic Flat-Ground Locomotion (PDF Sprint 1)
Train PPO policy for a quadruped (ANYmal-D or Unitree Go2) to walk on flat terrain.
Success criteria: robot walks forward without falling.

### Phase 2 — Rough Terrain + AMP (PDF Sprint 2)
Add terrain curriculum, use Adversarial Motion Priors for natural gaits.

### Phase 3 — Sim2Real Transfer (PDF Sprint 3)
Domain randomization, system identification, deploy to real hardware.

### Phase 4 — Whole-Body Control (PDF Sprint 4)
Combine locomotion with manipulation tasks.

### Phase 5 — Advanced Topics (PDF Sprint 5)
Multi-agent, human-robot interaction, foundation models for embodied AI.
