# Phase 1: ANYmal-D Flat Terrain Locomotion Training

## Overview

We trained an **ANYmal-D quadruped robot** to walk on flat ground using **PPO (Proximal Policy Optimization)**, a reinforcement learning algorithm. The robot learns by trial-and-error across **4,096 parallel simulations** running simultaneously on the GPU.

No custom code was written — this uses Isaac Lab's built-in task `Isaac-Velocity-Flat-Anymal-D-v0` with the standard `rsl_rl` training framework.

### Commands Used

```bash
# Training (inside isaac-lab container)
cd /workspace/isaaclab && ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-Flat-Anymal-D-v0 --num_envs 4096 --headless

# Evaluation + video recording
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py \
  --task Isaac-Velocity-Flat-Anymal-D-Play-v0 --num_envs 32 \
  --load_run 2026-03-03_09-38-16 --headless --video --enable_cameras
```

## Training Setup

| Parameter | Value |
|-----------|-------|
| Algorithm | PPO (on-policy) |
| Parallel envs | 4,096 |
| Iterations | 300 |
| Steps per env per iteration | 24 |
| Episode length | 20 seconds |
| Physics timestep | 0.005s (200 Hz), decimation=4 so policy runs at **50 Hz** |
| Training time | ~7 minutes on RTX 4090 |
| Final reward | 20.63 |
| Final episode length | 985/1000 steps |
| Base contact termination | 3.4% (robot rarely falls) |

## Neural Network (Actor-Critic)

Both the **actor** (picks actions) and **critic** (estimates value) are MLPs with 3 hidden layers of 128 neurons each, using ELU activation:

```
Observations (48-dim) → [128] → [128] → [128] → Joint Position Actions (12-dim)
```

Key PPO hyperparameters:

| Parameter | Value |
|-----------|-------|
| Learning rate | 0.001 (adaptive schedule) |
| Gamma (discount) | 0.99 |
| Lambda (GAE) | 0.95 |
| Entropy coefficient | 0.005 |
| Clip parameter | 0.2 |
| Mini-batches | 4 |
| Learning epochs per iteration | 5 |

## What the Robot Sees (Observations)

The policy receives 7 types of input, all with noise added to simulate real sensor imperfections:

| Observation | Noise range | Purpose |
|-------------|-------------|---------|
| Base linear velocity | ±0.1 | How fast the body moves |
| Base angular velocity | ±0.2 | How fast the body rotates |
| Projected gravity | ±0.05 | Which way is "up" (body tilt) |
| Velocity command | none | Target speed the robot should follow |
| Joint positions (relative) | ±0.01 | Current leg angles |
| Joint velocities (relative) | ±1.5 | Current leg speeds |
| Last action | none | What the policy commanded last step |

## What the Robot Does (Actions)

The output is **12 joint position targets** (3 joints per leg x 4 legs):

- **HAA** — Hip Abduction/Adduction (legs in/out)
- **HFE** — Hip Flexion/Extension (legs forward/back)
- **KFE** — Knee Flexion/Extension (knee bend)

These are scaled by 0.5 and added to the default standing pose.

## Reward & Punishment Strategy

The total reward each step is a weighted sum of individual terms. The design creates a clear hierarchy: stay alive > stay upright > follow commands > walk properly > be efficient.

### Rewards (positive weight = "do more of this")

| Reward | Weight | Formula | Purpose |
|--------|--------|---------|---------|
| **Track linear velocity XY** | **+1.0** | `exp(-‖v_xy - v_cmd‖² / 0.5)` | Follow the commanded forward/lateral speed |
| **Track angular velocity Z** | **+0.5** | `exp(-‖ω_z - ω_cmd‖² / 0.5)` | Follow the commanded turning rate |
| **Feet air time** | **+0.5** | reward when feet lift >0.5s | Encourage proper stepping gait (not shuffling) |

### Punishments (negative weight = "don't do this")

| Punishment | Weight | Formula | Purpose |
|------------|--------|---------|---------|
| **Flat orientation** | **-5.0** | `‖gravity_xy‖²` | Don't tilt the body — stay upright |
| **Vertical velocity** | **-2.0** | `v_z²` | Don't bounce up and down |
| **Undesired contacts (thighs)** | **-1.0** | penalize if thigh force > 1N | Don't drag thighs on the ground |
| **Action rate** | **-0.01** | `‖a_t - a_{t-1}‖²` | Don't jerk — smooth motions |
| **Angular velocity XY** | **-0.05** | `‖ω_xy‖²` | Don't roll or pitch rapidly |
| **Joint torques** | **-2.5e-5** | `‖τ‖²` | Don't use excessive motor force |
| **Joint accelerations** | **-2.5e-7** | `‖q̈‖²` | Don't have jerky joint motion |

### Termination (instant episode reset)

| Condition | Effect |
|-----------|--------|
| **Base contact** | If the robot's body touches the ground (force > 1N), the episode is **immediately terminated**. This is the harshest punishment — the robot loses all future reward. |
| **Time out** | Episode ends after 20s (not a punishment, just a reset) |

## Domain Randomization

Makes the policy robust rather than memorizing one specific scenario.

### On startup (once per env):

- **Body mass**: ±5 kg added to the base (robot must handle being heavier/lighter)
- **Center of mass**: shifted ±5cm in X/Y, ±1cm in Z
- **Friction**: static 0.8, dynamic 0.6

### During episodes:

- **Random pushes**: every 10-15 seconds, the robot gets shoved at ±0.5 m/s
- **Random reset pose/velocity**: episodes start at random positions and orientations

## Velocity Commands

The robot receives random velocity commands, resampled every 10 seconds:

| Command | Range |
|---------|-------|
| Forward/backward speed | -1.0 to 1.0 m/s |
| Lateral speed | -1.0 to 1.0 m/s |
| Turning rate | -1.0 to 1.0 rad/s |
| Heading | -π to π |

2% of envs receive a "stand still" command to also learn standing.

## Robot Details

- **Model**: ANYmal-D by ANYbotics
- **Actuators**: LSTM-based actuator network (`anydrive_3_lstm_jit.pt`) that models real motor dynamics
- **Effort limit**: 80 Nm per joint, saturation at 120 Nm
- **Velocity limit**: 7.5 rad/s per joint
- **Initial pose**: standing at 0.6m height with default joint angles

## Output Files

```
training/anymal_d_flat/
├── checkpoints/
│   └── model_299.pt          — Final trained model (300 iterations)
├── params/
│   ├── agent.yaml             — PPO hyperparameters
│   └── env.yaml               — Full environment config
├── exported/
│   ├── policy.pt              — Exported policy for deployment
│   └── policy.onnx            — ONNX format for Sim2Real / edge inference
└── events.out.tfevents.*      — TensorBoard training logs

assets/
├── anymal_d_flat_walking.mp4  — Training result video
└── rl-video-step-0.mp4        — Raw evaluation recording
```
