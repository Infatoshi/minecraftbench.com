"""Harness self-tests: mcbd roundtrip, validation, diff metric properties, baselines."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))

from blockclass import CLASS_NAMES, CLASS_OF  # noqa: E402
from diff import diff as diff_fn  # noqa: E402
from mcbd import CHUNK_U16, read_mcbd, write_mcbd  # noqa: E402


def _random_dump(path, seed=42, cx0=-1, cz0=-1, cx1=1, cz1=1):
    rng = np.random.default_rng(seed)
    n = (cx1 - cx0 + 1) * (cz1 - cz0 + 1) * CHUNK_U16
    # ids drawn from real classes so per-class metrics exercise multiple rows
    ids = rng.choice(np.array([0, 1, 2, 3, 7, 8, 12, 17, 18, 31, 56], dtype=np.uint16), size=n)
    meta = rng.integers(0, 16, size=n, dtype=np.uint16)
    blocks = (ids << 4) | meta
    write_mcbd(path, seed, cx0, cz0, cx1, cz1, 0, blocks)
    return blocks


def _run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, cwd=HARNESS)


def test_roundtrip_bitwise(tmp_path):
    p = tmp_path / "a.mcbd"
    blocks = _random_dump(p)
    d = read_mcbd(p)
    assert d.seed == 42 and (d.cx0, d.cz0, d.cx1, d.cz1, d.dim) == (-1, -1, 1, 1, 0)
    assert d.blocks.dtype == np.uint16
    assert np.array_equal(d.blocks, blocks)


def test_truncated_rejected(tmp_path):
    p = tmp_path / "a.mcbd"
    _random_dump(p)
    raw = p.read_bytes()
    (tmp_path / "trunc.mcbd").write_bytes(raw[:-100])
    with pytest.raises(ValueError):
        read_mcbd(tmp_path / "trunc.mcbd")
    (tmp_path / "badmagic.mcbd").write_bytes(b"NOTMAGIC" + raw[8:])
    with pytest.raises(ValueError):
        read_mcbd(tmp_path / "badmagic.mcbd")


def test_wrong_size_write():
    with pytest.raises(ValueError):
        write_mcbd("/dev/null", 1, 0, 0, 0, 0, 0, np.zeros(7, dtype=np.uint16))


def test_header_mismatch_exit2(tmp_path):
    a, b = tmp_path / "a.mcbd", tmp_path / "b.mcbd"
    _random_dump(a, seed=1)
    _random_dump(b, seed=2)
    r = _run(HARNESS / "diff.py", a, b)
    assert r.returncode == 2
    assert "mismatch" in r.stderr


def test_self_diff_is_100(tmp_path):
    p = tmp_path / "a.mcbd"
    _random_dump(p)
    d = read_mcbd(p)
    m = diff_fn(d, d)
    assert m["raw_match_pct"] == 100.0
    assert m["macro_accuracy_pct"] == 100.0
    for row in m["per_class"].values():
        assert row["match_count"] == row["oracle_count"]


def test_pair_histogram_sums(tmp_path):
    a, b = tmp_path / "a.mcbd", tmp_path / "b.mcbd"
    _random_dump(a, seed=7)
    blocks = _random_dump(b, seed=7)  # same header
    # perturb candidate
    blocks = blocks.copy()
    blocks[::3] = 1 << 4
    write_mcbd(b, 7, -1, -1, 1, 1, 0, blocks)
    o, c = read_mcbd(a), read_mcbd(b)
    m = diff_fn(o, c)
    # few enough classes in play that top20 covers every nonzero pair
    assert sum(row[2] for row in m["pair_histogram_top20"]) == o.blocks.size


def test_baselines_and_base_rate(tmp_path):
    """all_stone vs superflat: raw match is high (shared air+bedrock), macro is low."""
    a, b = tmp_path / "stone.mcbd", tmp_path / "flat.mcbd"
    for script, out in ((HARNESS / "baselines" / "all_stone.py", a),
                        (HARNESS / "baselines" / "superflat.py", b)):
        r = _run(script, "--seed", 5, "--cx0", 0, "--cz0", 0, "--cx1", 1, "--cz1", 1,
                 "--out", out)
        assert r.returncode == 0, r.stderr
    r = _run(HARNESS / "diff.py", a, b)
    assert r.returncode == 0, r.stderr
    m = json.loads(r.stdout)
    assert m["macro_accuracy_pct"] < m["raw_match_pct"]
    # superflat's dirt/grass layers are all wrong in all_stone's world and vice versa
    assert m["per_class"]["stone-family"]["accuracy_pct"] == 0.0


def test_class_table_sane():
    assert CLASS_OF[0] == "air" and CLASS_OF[1] == "stone-family"
    assert CLASS_OF[3] == "dirt/grass"  # dirt is NOT stone-family
    assert CLASS_NAMES[-1] == "other"
    assert len(set(CLASS_NAMES)) == len(CLASS_NAMES)
