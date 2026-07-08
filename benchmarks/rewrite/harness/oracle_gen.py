"""Eval-time oracle: generate a fresh 1.11.2 world at SEED with the real Java game, headless,
structures off, and convert the pregen region to a canonical .mcbd dump.

The oracle lives in the PRIVATE repo (decompiled Mojang source - never vendored here); this
wrapper only drives it. Set MCBENCH_ORACLE_ROOT (default ~/dev/minecraft/mc-1.11.2-env).

Usage:
  uv run --with numpy --with nbt --with pyyaml python oracle_gen.py --seed 123456789 --out oracle.mcbd
  # window is auto-discovered from the save (pregen centers on SPAWN, not the origin);
  # override with --cx0/--cz0/--cx1/--cz1

Protocol (every step is a hard-won gotcha from the private repo's DEVLOG):
  1. wipe saves/qrl_<seed> (qrl reset REUSES existing folders; stale level.dat lies)
  2. ensure Xvfb :1 (worldgen needs the client; software GL, stays off the shared GPU)
  3. launch runClient detached via setsid (chained launch+poll returns exit 255 over ssh)
  4. poll the qrl TCP bridge (127.0.0.1:25575), reset with the seed, wait for ok (~40s pregen)
  5. close_world() -> loadWorld(null) -> save flush. NEVER kill -9 (loses region files)
  6. pkill -f '[G]radleStart' (bracket-escaped so nothing self-matches)
  7. parse region/*.mca -> .mcbd via mca2mcbd
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ORACLE_ROOT = Path(os.environ.get("MCBENCH_ORACLE_ROOT", os.path.expanduser("~/dev/minecraft/mc-1.11.2-env")))
QRL_PORT = 25575
LAUNCH_TIMEOUT_S = 420  # gradle + JVM boot
PREGEN_TIMEOUT_S = 240


def qrl_cmd(payload: dict, timeout: float = 15.0) -> dict:
    """One request/response on the qrl bridge (newline-JSON, matches qrl_client.py)."""
    with socket.create_connection(("127.0.0.1", QRL_PORT), timeout=timeout) as s:
        f = s.makefile("rwb")
        f.write((json.dumps(payload) + "\n").encode())
        f.flush()
        line = f.readline()
    if not line:
        raise ConnectionError("qrl bridge closed")
    return json.loads(line.decode())


def port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", QRL_PORT), timeout=1.0):
            return True
    except OSError:
        return False


def ensure_xvfb() -> None:
    if subprocess.run(["pgrep", "-f", "[X]vfb :1"], capture_output=True).returncode != 0:
        subprocess.Popen(
            ["Xvfb", ":1", "-screen", "0", "1280x720x24", "+extension", "GLX"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        time.sleep(2)


def kill_game() -> None:
    subprocess.run(["pkill", "-f", "[G]radleStart"], capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--cx0", type=int)
    ap.add_argument("--cz0", type=int)
    ap.add_argument("--cx1", type=int)
    ap.add_argument("--cz1", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-save", action="store_true")
    args = ap.parse_args()

    if not ORACLE_ROOT.is_dir():
        print(f"oracle root not found: {ORACLE_ROOT} (set MCBENCH_ORACLE_ROOT)", file=sys.stderr)
        return 2

    run_dir = ORACLE_ROOT / "java" / "Minecraft" / "run"
    save_dir = run_dir / "saves" / f"qrl_{args.seed}"
    region_dir = save_dir / "region"

    # 1. fresh folder per seed
    if save_dir.exists():
        shutil.rmtree(save_dir)

    # 2-3. display + detached launch
    ensure_xvfb()
    kill_game()
    time.sleep(2)
    t0 = time.time()
    launch = (
        f"cd {ORACLE_ROOT / 'java'} && setsid nohup uv run --no-project --with pyyaml "
        f"python mc_cli.py --set world.seed={args.seed} --set world.structures=false "
        f"--set world.type=default >/tmp/mcbench_oracle_launch.log 2>&1 </dev/null &"
    )
    subprocess.run(["bash", "-c", launch], check=True)

    # 4. wait for bridge, then drive the reset
    while not port_open():
        if time.time() - t0 > LAUNCH_TIMEOUT_S:
            print("timeout waiting for qrl bridge; see /tmp/mcbench_oracle_launch.log", file=sys.stderr)
            return 3
        time.sleep(3)
    t1 = time.time()
    world = {"seed": args.seed, "type": "default", "structures": False}
    while True:
        r = qrl_cmd({"cmd": "reset", "world": world})
        if r.get("ok"):
            break
        if not r.get("loading"):
            print(f"reset error: {r}", file=sys.stderr)
            return 4
        if time.time() - t1 > PREGEN_TIMEOUT_S:
            print(f"timeout waiting for world pregen: {r}", file=sys.stderr)
            return 4
        time.sleep(2)
    gen_s = time.time() - t1

    # 5-6. flush save, stop gently
    try:
        qrl_cmd({"cmd": "close"})
    except OSError:
        pass
    time.sleep(5)
    kill_game()
    deadline = time.time() + 60
    while time.time() < deadline:
        if subprocess.run(["pgrep", "-f", "[G]radleStart"], capture_output=True).returncode != 0:
            break
        time.sleep(2)

    if not region_dir.is_dir():
        print(f"no region dir after generation: {region_dir}", file=sys.stderr)
        return 5

    # 7. convert (auto window unless explicitly overridden)
    here = Path(__file__).parent
    if None in (args.cx0, args.cz0, args.cx1, args.cz1):
        window = ["--auto"]
    else:
        window = ["--cx0", str(args.cx0), "--cz0", str(args.cz0),
                  "--cx1", str(args.cx1), "--cz1", str(args.cz1)]
    conv = subprocess.run(
        [
            "uv", "run", "--no-project", "--with", "numpy", "--with", "nbt", "python",
            str(here / "mca2mcbd.py"), "--region", str(region_dir), "--seed", str(args.seed),
            *window, "--out", args.out,
        ],
        cwd=here,
    )
    if conv.returncode != 0:
        return conv.returncode
    if not args.keep_save:
        shutil.rmtree(save_dir, ignore_errors=True)
    print(f"oracle dump complete: seed={args.seed} pregen={gen_s:.0f}s total={time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
