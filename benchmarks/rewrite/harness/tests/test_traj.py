"""traj_diff unit tests on tiny synthetic recordings (1 chunk, 8x8 frames)."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcbd import write_mcbd  # noqa: E402
import traj_diff  # noqa: E402

KF = [0, 20]


def write_frame(path, shade):
    from PIL import Image
    Image.fromarray(np.full((8, 8, 3), shade, dtype=np.uint8)).save(path)


def make_rec(d, *, state_mut=None, blocks_mut=None, shade=100):
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({"keyframes": KF, "ticks": 40}))
    for t in KF:
        s = {"tick": t, "x": 0.5, "y": 64.0, "z": 0.5, "yaw": 0.0, "health": 20.0,
             "air": 300, "time": {"world_time": 1000, "total_time": 170 + t}}
        if state_mut:
            state_mut(s, t)
        (d / f"state_{t}.json").write_text(json.dumps(s))
        blocks = np.zeros(16 * 16 * 256, dtype=np.uint16)
        blocks[:256] = (1 << 4)  # stone floor
        blocks[300] = (18 << 4) | 0x9  # leaves, check-decay bit set
        if blocks_mut:
            blocks_mut(blocks, t)
        write_mcbd(d / f"world_{t}.mcbd", 42, 0, 0, 0, 0, 0, blocks)
        write_frame(d / f"frame_{t}.png", shade)


def test_identical_is_perfect(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c")
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == 20
    assert r["state_match_pct"] == 100.0
    assert r["block_match_pct"] == 100.0
    assert r["pixel_tier_pct"] == {"strict": 100.0, "loose": 100.0, "structural": 100.0}


def test_excluded_fields_ignored(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c",
             state_mut=lambda s, t: (s.update(air=1),
                                     s["time"].update(total_time=999999)))
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == 20
    assert r["state_match_pct"] == 100.0


def test_leaf_check_decay_bit_masked(tmp_path):
    make_rec(tmp_path / "o")

    def clear_bit(blocks, t):
        blocks[300] = (18 << 4) | 0x1  # same leaves, check-decay bit clear
    make_rec(tmp_path / "c", blocks_mut=clear_bit)
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["block_match_pct"] == 100.0
    assert r["last_match_tick"] == 20


def test_state_divergence_sets_last_match(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c",
             state_mut=lambda s, t: s.update(y=65.0) if t == 20 else None)
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == 0
    assert 0 < r["state_match_pct"] < 100.0


def test_block_divergence_sets_last_match(tmp_path):
    make_rec(tmp_path / "o")

    def dig(blocks, t):
        if t == 20:
            blocks[0] = 0
    make_rec(tmp_path / "c", blocks_mut=dig)
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == 0
    assert r["state_match_pct"] == 100.0  # state never gates on blocks


def test_stub_diverges_at_first_keyframe(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c", state_mut=lambda s, t: s.update(x=999.0))
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == -1


def test_unsimulated_null_counts_honestly(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c", state_mut=lambda s, t: s.update(health=None))
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == -1  # not exact
    kf = r["per_keyframe"][0]["state"]
    assert kf["unsimulated"] == 1
    assert kf["mismatched"] == []  # null is honest, not a lie


def test_pixel_tiers(tmp_path):
    make_rec(tmp_path / "o", shade=100)
    make_rec(tmp_path / "c", shade=125)  # mean diff 25/channel: fails strict, passes loose
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["pixel_tier_pct"]["strict"] == 0.0
    assert r["pixel_tier_pct"]["loose"] == 100.0
    assert r["last_match_tick"] == 20  # pixels never gate state/blocks


def test_missing_artifacts_score_zero(tmp_path):
    make_rec(tmp_path / "o")
    (tmp_path / "c").mkdir()
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == -1
    assert r["block_match_pct"] == 0.0
    assert r["pixel_tape_mean"] is None


def test_window_mismatch_is_not_exact(tmp_path):
    make_rec(tmp_path / "o")
    make_rec(tmp_path / "c")
    blocks = np.zeros(4 * 16 * 16 * 256, dtype=np.uint16)
    for t in KF:
        write_mcbd(tmp_path / "c" / f"world_{t}.mcbd", 42, 0, 0, 1, 1, 0, blocks)
    r = traj_diff.score(tmp_path / "o", tmp_path / "c")
    assert r["last_match_tick"] == -1
    assert r["block_match_pct"] == 0.0
