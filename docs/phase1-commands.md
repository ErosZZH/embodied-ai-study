# Phase 1: Complete Command Sequence

Every command executed on the remote VM to go from zero to a trained walking robot.

## Prerequisites

```bash
# SSH into the server
ssh ubuntu@117.50.171.225
```

The server already had:
- NVIDIA RTX 4090 with driver 575.57.08
- Docker with `isaac-sim` container (came with the GPU rental image)
- Docker compose at `/home/ubuntu/docker-compose.yml`

---

## Step 1: Launch Isaac Lab Container

The `isaac-sim` container (for livestreaming) was pre-installed. We needed a separate `isaac-lab` container for RL training.

```bash
# Pull and run the Isaac Lab container
sudo docker run -d --name isaac-lab \
  --gpus all \
  --network host \
  -e ACCEPT_EULA=Y \
  -e PRIVACY_CONSENT=Y \
  -v /home/ubuntu/isaac-lab-data/logs:/workspace/isaaclab/logs:rw \
  nvcr.io/nvidia/isaac-lab:2.3.2
```

Key details:
- **Image**: `nvcr.io/nvidia/isaac-lab:2.3.2` (includes Isaac Sim 5.1 + Isaac Lab + rsl_rl + everything needed)
- **Volume mount**: Maps `~/isaac-lab-data/logs` so training logs persist outside the container
- **GPU**: Full GPU passthrough

## Step 2: Verify the Setup

```bash
# Check container is running
sudo docker ps | grep isaac-lab

# Verify GPU is visible inside container
sudo docker exec isaac-lab bash -c 'nvidia-smi'

# Check Isaac Lab version
sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p -c "import isaaclab; print(isaaclab.__version__)"'
# Output: 0.54.2

# Check available tasks
sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p scripts/tools/list_envs.py | grep -i anymal'
# Output shows: Isaac-Velocity-Flat-Anymal-D-v0, Isaac-Velocity-Rough-Anymal-D-v0, etc.
```

## Step 3: Train the Policy

This is the main training command. One single command, takes ~7 minutes.

```bash
sudo docker exec isaac-lab bash -c '
  cd /workspace/isaaclab && \
  ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Velocity-Flat-Anymal-D-v0 \
    --num_envs 4096 \
    --headless
'
```

What this does:
- `--task Isaac-Velocity-Flat-Anymal-D-v0` — Built-in ANYmal-D flat terrain locomotion task
- `--num_envs 4096` — Run 4096 robots in parallel (maximizes GPU utilization)
- `--headless` — No GUI needed (we're on a headless server)

The training runs **300 iterations** by default (configured in the task's agent config). Output goes to `/workspace/isaaclab/logs/rsl_rl/anymal_d_flat/<timestamp>/`.

### Training Output

During training, you'll see output like:

```
Learning iteration 0/300
  mean reward:  -9.42
  mean episode length:  78.3
  ...
Learning iteration 50/300
  mean reward:  2.15
  mean episode length:  198.5
  ...
Learning iteration 299/300
  mean reward:  20.63
  mean episode length:  985.2
```

Checkpoints are saved every 50 iterations: `model_0.pt`, `model_50.pt`, ..., `model_299.pt`.

## Step 4: Evaluate and Record Video

After training, run the policy and record a video:

```bash
# Find the training run name (timestamp directory)
sudo docker exec isaac-lab bash -c 'ls /workspace/isaaclab/logs/rsl_rl/anymal_d_flat/'
# Output: 2026-03-03_09-38-16

# Play the trained policy and record video
sudo docker exec isaac-lab bash -c '
  cd /workspace/isaaclab && \
  ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py \
    --task Isaac-Velocity-Flat-Anymal-D-Play-v0 \
    --num_envs 32 \
    --load_run 2026-03-03_09-38-16 \
    --headless \
    --video \
    --enable_cameras
'
```

What this does:
- `Isaac-Velocity-Flat-Anymal-D-Play-v0` — The evaluation variant of the task (note the `-Play` suffix)
- `--num_envs 32` — Only 32 robots for visualization (less GPU memory needed for rendering)
- `--load_run <timestamp>` — Load the trained checkpoint
- `--video --enable_cameras` — Record an MP4 video

Video saved to: `logs/rsl_rl/anymal_d_flat/<timestamp>/videos/play/rl-video-step-0.mp4`

## Step 5: Export Policy for Deployment

```bash
# Export to ONNX (for Sim2Real / edge devices)
sudo docker exec isaac-lab bash -c '
  cd /workspace/isaaclab && \
  ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py \
    --task Isaac-Velocity-Flat-Anymal-D-Play-v0 \
    --num_envs 1 \
    --load_run 2026-03-03_09-38-16 \
    --headless
'
```

The exported files (`policy.pt` and `policy.onnx`) are saved to the `exported/` subdirectory of the run.

## Step 6: Copy Results to Host

```bash
# The logs volume is already mounted, so files are accessible at:
ls ~/isaac-lab-data/logs/rsl_rl/anymal_d_flat/2026-03-03_09-38-16/

# Copy the video to a convenient location
sudo cp ~/isaac-lab-data/logs/rsl_rl/anymal_d_flat/2026-03-03_09-38-16/videos/play/rl-video-step-0.mp4 \
  ~/isaac-lab-data/anymal_d_flat_walking.mp4

# Copy the best checkpoint
mkdir -p ~/isaac-lab-data/checkpoints
sudo cp ~/isaac-lab-data/logs/rsl_rl/anymal_d_flat/2026-03-03_09-38-16/model_299.pt \
  ~/isaac-lab-data/checkpoints/anymal_d_flat_model_299.pt
```

## Step 7: Monitor with TensorBoard (Optional)

```bash
# Start TensorBoard inside the container
sudo docker exec -d isaac-lab bash -c '
  cd /workspace/isaaclab && \
  pip install tensorboard && \
  tensorboard --logdir logs --bind_all --port 6006
'

# From your LOCAL machine, create an SSH tunnel:
ssh -L 6006:localhost:6006 ubuntu@117.50.171.225

# Then open in browser: http://localhost:6006
```

---

## Quick Reference: Copy-Paste Version

If you want to redo the entire thing from scratch in one go:

```bash
# 1. SSH in
ssh ubuntu@117.50.171.225

# 2. Start Isaac Lab container (skip if already running)
sudo docker start isaac-lab

# 3. Train (7 min on RTX 4090)
sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py --task Isaac-Velocity-Flat-Anymal-D-v0 --num_envs 4096 --headless'

# 4. Record video
sudo docker exec isaac-lab bash -c 'cd /workspace/isaaclab && ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py --task Isaac-Velocity-Flat-Anymal-D-Play-v0 --num_envs 32 --load_run $(ls -t /workspace/isaaclab/logs/rsl_rl/anymal_d_flat/ | head -1) --headless --video --enable_cameras'

# 5. Copy video out from your local machine
scp ubuntu@117.50.171.225:~/isaac-lab-data/logs/rsl_rl/anymal_d_flat/*/videos/play/*.mp4 ./
```

## No Custom Code Was Written

This entire training uses Isaac Lab's built-in:
- **Task**: `Isaac-Velocity-Flat-Anymal-D-v0` (defined in `isaaclab_tasks` package)
- **Training script**: `scripts/reinforcement_learning/rsl_rl/train.py`
- **Evaluation script**: `scripts/reinforcement_learning/rsl_rl/play.py`
- **RL algorithm**: `rsl_rl` (PPO implementation by RSL at ETH Zurich)
- **Robot model**: ANYmal-D USD asset from NVIDIA's asset server

All configuration (rewards, observations, domain randomization) comes from the task's Python config class, which we dumped to `params/env.yaml` and `params/agent.yaml` during training.
