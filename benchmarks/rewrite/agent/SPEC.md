# SPEC - what you are building

A from-scratch reimplementation of Minecraft 1.11.2 (Java Edition) as a batched, vectorized RL
environment in C/C++/CUDA (Rust acceptable), targeting the machine you are on. The deliverable
runs with no network and no JVM, and must contain no Minecraft source code in any form
(decompiled or otherwise) - that is scanned for and voids the run. Open-source code that is
not Minecraft source (libraries, reference reimplementations) is fair game to fetch, vendor,
and build on; license headers stay intact. Your knowledge of the game is the spec for
behavior; where you are unsure, prefer vanilla 1.11.2 semantics.

## Deliverables

A repo that builds with `make` at the root, producing:

1. `libmcbench.so` - vectorized env ABI (C symbols):
   - `void* mcb_make(int num_envs, uint64_t seed);`
   - `void  mcb_reset(void* h);`
   - `void  mcb_step(void* h, const McbAction* actions);`  // one action per env, one tick
   - `void  mcb_obs(void* h, McbObs* out);`                // fills per-env observation structs
   - `int   mcb_dump_world(void* h, int env_idx, int cx0, int cz0, int cx1, int cz1, uint16_t* out);`
   - `int   mcb_render(void* h, int env_idx, int width, int height, uint8_t* rgba_out);`
     // first-person frame from the env's current pose/tick, row-major RGBA8
   - `void  mcb_close(void* h);`
   - McbAction: uint8 forward, back, left, right, jump, sneak, sprint, attack, use;
     int8 hotbar (-1 = no change, else 0-8); int8 dyaw, dpitch (units of 15 degrees).
   - McbObs: double x, y, z; float yaw, pitch; float vx, vy, vz; uint8 on_ground;
     float health; int32 food, air, xp; uint8 dead; int32 dim.
   - Exact struct definitions in `mcbench.h` (write it; the verifier compiles against it).

2. `./mcbench` CLI (thin wrapper over the lib):
   - `./mcbench --dump-world --seed S --cx0 A --cz0 B --cx1 C --cz1 D --out FILE`
     writes the canonical .mcbd dump (format below).
   - `./mcbench --sps --num-envs N --ticks T --seed S` prints steady-state env-steps/sec.
   - `./mcbench --render-frame --seed S --x X --y Y --z Z --yaw A --pitch B --width W
     --height H --out FILE.png` writes one frame (PNG, RGBA8) via mcb_render.

## Canonical dump format (.mcbd)

Little-endian: magic "MCBDUMP1"; u64 seed; i32 cx0, cz0, cx1, cz1 (inclusive); u32 dim (0 =
overworld); u32 reserved = 0; then u16 blocks: for cz in cz0..cz1, for cx in cx0..cx1, one
chunk of 16*16*256 values indexed (y*16 + z)*16 + x. Value = (blockId << 4) | meta using
vanilla 1.11.2 numeric ids. Air = 0.

## Worldgen requirements (verified first, weighted heavily)

Overworld worldgen for arbitrary 64-bit seeds must match vanilla 1.11.2 with structures OFF:
biome layout, terrain shape, surface blocks, carving (caves/ravines), and decoration (ores,
trees, lakes, features). Seed-faithful worldgen requires replicating Java's 48-bit LCG
java.util.Random and vanilla's exact draw order.

## Sim requirements

Player physics (movement, gravity, collision, jumping, sneaking, sprinting), block dig/place,
falling blocks, water/lava flow, day/night tick, health/food/fall damage. 20 ticks per second
semantics; one mcb_step = one tick. Determinism: same seed + same action sequence = identical
state, and results must be identical for any num_envs.

## Performance

The point of the exercise: batched throughput on this machine's GPU (check nvidia-smi; use the
RTX 3090, sm_86). Aggregate env-steps/sec across N envs is your score multiplier - a correct
but slow env scores poorly. The reference Java game does ~881 TPS single-world on this CPU;
you are expected to beat it by orders of magnitude in aggregate.

## Budget

Your run has a fixed budget; the harness will stop you when it is exhausted. Leave the repo
building and the CLI working at all times - the verifier runs whatever is on disk when time is
called.
