"""Level suites (D26): config, job lists, building with caching, loading back, gallery images."""

from pathlib import Path

import pygame
import pytest

from stereo_flyness.game import suites
from stereo_flyness.game.bot import replay
from stereo_flyness.game.generator import GENERATOR_VERSION
from stereo_flyness.viewer.overview import draw_overview

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "level_suites.toml"


def test_committed_config_matches_the_generator_and_the_agreed_sizes():
    config = suites.load_config(CONFIG)
    counts = {}
    for job in suites.jobs(config):
        counts[(job.suite, job.kind)] = counts.get((job.suite, job.kind), 0) + 1
    assert all(counts[("training", k)] == 50 for k in suites.KINDS)
    assert all(counts[("held_out", k)] == 20 for k in suites.KINDS)


def test_training_and_held_out_seeds_never_overlap():
    config = suites.load_config(CONFIG)
    train = {(j.kind, j.difficulty, j.seed) for j in suites.jobs(config, "training")}
    held = {(j.kind, j.difficulty, j.seed) for j in suites.jobs(config, "held_out")}
    assert train and held and not train & held


def test_config_for_another_generator_version_is_rejected(tmp_path):
    bad = tmp_path / "suites.toml"
    bad.write_text(CONFIG.read_text().replace(f"generator_version = {GENERATOR_VERSION}", "generator_version = 1"))
    with pytest.raises(ValueError, match="generator"):
        suites.load_config(bad)


def test_limit_caps_jobs_per_kind_and_difficulty():
    config = suites.load_config(CONFIG)
    assert len(suites.jobs(config, "training", limit=1)) == 9  # 3 kinds x 3 difficulties


def test_build_caches_and_loads_back(tmp_path):
    job = suites.Job("training", "cube", "easy", 0)
    assert not suites.is_built(tmp_path, job)
    row = suites.build(job, tmp_path, seconds=15)
    assert suites.is_built(tmp_path, job) and suites.load_row(tmp_path, job) == row
    assert row["generator_version"] == GENERATOR_VERSION and row["tightest_window_ms"] >= 100
    level, bot = suites.load_level(tmp_path, job)
    assert level.name == "cube-easy-0"
    assert replay(level, bot).summary.completed  # the saved bot inputs still beat the saved level


def test_overview_draws_level_and_path_headless(tmp_path):
    job = suites.Job("training", "cube", "easy", 1)
    suites.build(job, tmp_path, seconds=15)
    level, bot = suites.load_level(tmp_path, job)
    surface = draw_overview(level, replay(level, bot))
    assert surface.get_width() == 1800 and surface.get_height() > 300
    assert len(set(pygame.image.tobytes(surface, "RGB"))) > 3  # more than a blank background
