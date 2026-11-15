"""Iteration 1's levels must rebuild exactly as the fly played them, and iteration 2's exactly as frozen before any run (iteration2_levels.md).

tests/data/v3_level_hashes.json holds one SHA-256 per level of the iteration-1 suites (training and
held-out; cube, ship and mixed), recorded by scripts/freeze_level_hashes.py from the cached levels
the runs used. Each level is rebuilt here from its seed and the attempt the bot accepted.

If this fails, the generator has changed the old levels. Fix the generator (put new chunks behind a
new version) instead of re-recording the hashes.
"""

import json
from pathlib import Path

import pytest

from stereo_flyness.game import suites
from stereo_flyness.game.generator import BUILDERS

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads((ROOT / "tests" / "data" / "v3_level_hashes.json").read_text())
JOBS = suites.jobs(suites.load_config(ROOT / "configs" / "level_suites.toml"))


def test_every_iteration1_level_is_frozen():
    assert len(JOBS) == 210
    assert {f"{j.suite}/{j.name}" for j in JOBS} == set(FROZEN["levels"])
    assert all(j.generator_version == 3 for j in JOBS)


@pytest.mark.parametrize("job", JOBS, ids=lambda j: f"{j.suite}/{j.name}")
def test_iteration1_level_rebuilds_unchanged(job):
    frozen = FROZEN["levels"][f"{job.suite}/{job.name}"]
    level = BUILDERS[job.kind](job.seed, job.difficulty, FROZEN["seconds"], frozen["attempt"],
                               version=frozen["generator_version"])
    assert suites.level_hash(level) == frozen["sha256"]


# -- iteration 2 (v4): frozen before any run (Shannyn, 2026-11-15) ----------------------

FROZEN_V4 = json.loads((ROOT / "tests" / "data" / "v4_level_hashes.json").read_text())
JOBS_V4 = suites.jobs(suites.load_config(ROOT / "configs" / "iteration2" / "level_suites.toml"))


def test_every_iteration2_level_is_frozen():
    assert len(JOBS_V4) == 90
    assert {f"{j.suite}/{j.name}" for j in JOBS_V4} == set(FROZEN_V4["levels"])
    assert all(j.generator_version == 4 for j in JOBS_V4)


@pytest.mark.parametrize("job", JOBS_V4, ids=lambda j: f"{j.suite}/{j.name}")
def test_iteration2_level_rebuilds_unchanged(job):
    frozen = FROZEN_V4["levels"][f"{job.suite}/{job.name}"]
    level = BUILDERS[job.kind](job.seed, job.difficulty, FROZEN_V4["seconds"], frozen["attempt"],
                               version=frozen["generator_version"])
    assert suites.level_hash(level) == frozen["sha256"]
