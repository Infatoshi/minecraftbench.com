# Run sandbox (anvil)

The agent runs bare-metal as dedicated user `mcbench` - real hardware view, working
profilers, zero virtualization tax. Run-time isolation protects the shared box and the
private oracle repo; eval integrity comes from the time-seed protocol (SPEC 6/7), not from
this sandbox. The eval-time candidate dump is the only containerized step (eval/Dockerfile,
`--network none`).

## One-time setup (done 2026-07-08)

```
sudo useradd -m -s /bin/bash mcbench
sudo usermod -aG video,render mcbench        # /dev/nvidia* access
sudo chmod 750 /home/infatoshi               # oracle repo + secrets unreachable
sudo -u mcbench bash -lc 'npm config set prefix ~/.local && npm install -g @openai/codex'
```

Verified: mcbench runs CUDA kernels on the 3090 (sm_86), `ls /home/infatoshi` -> permission
denied. GPU perf counters already open to non-admin (RmProfilingAdminOnly=0), so ncu/nsys
work unprivileged.

## Per run

`run.sh` stages a fresh workdir (`/home/mcbench/runs/<id>`) holding exactly prompt.txt +
SPEC.md + VERIFIER.md as a git repo, copies harness auth into the sandbox home, and launches
the CLI under a systemd scope: MemoryMax=64G, CPUQuota=2400% (24/32 threads), TasksMax=8192,
CUDA_VISIBLE_DEVICES=1, `timeout` = the budget. `collect.sh` pulls the repo bundle, tree
snapshot, stdout log, and codex session transcripts into results/runs/<id>/.

## Knowingly soft (v1)

- GPU pinning is CUDA_VISIBLE_DEVICES only; a hard DeviceAllow cgroup rule is a follow-up.
- Harness auth tokens are readable by the agent (inherent to running any CLI as the sandbox
  user; grants API usage only).
- Network is open during the run: the harness CLI needs API egress, and there is nothing to
  exfiltrate - eval seeds postdate the run.
