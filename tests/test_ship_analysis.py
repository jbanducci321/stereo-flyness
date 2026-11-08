import numpy as np
import pandas as pd
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level, Portal
from stereo_flyness.game.recorder import play
from stereo_flyness.experiments.ship_analysis import (
    compare_runs, death_mode, hold_stats, replay_run, sections_reached)


def mixed_level():
    return Level("mixed", "test", 2000, [], [Portal("ship", 400, 45), Portal("cube", 1200, 45)])


def run_dict(log):
    return {"level": log.summary.level, "completed": log.summary.completed,
            "progress": log.summary.progress, "ticks": log.summary.ticks}


def test_replay_matches_and_refuses_a_wrong_record():
    level = mixed_level()
    log = play(Game(level), lambda g: g.ticks % 60 < 25)
    held = log.to_frame()["held"].to_numpy()
    assert replay_run(level, held, run_dict(log)).finished == log.summary.completed
    with pytest.raises(ValueError, match="ticks"):
        replay_run(level, held, {**run_dict(log), "ticks": log.summary.ticks + 1})


def test_compare_is_d48s_equal():
    done = {"completed": True, "progress": 1.0, "death_source_id": None}
    a = {"completed": False, "progress": 0.4, "death_source_id": 7}
    assert compare_runs(done, done) == 0 and compare_runs(done, a) == 1 and compare_runs(a, done) == -1
    assert compare_runs(a, {**a, "progress": 0.45}) == 0  # same object
    assert compare_runs(a, {**a, "death_source_id": 8, "progress": 0.3}) == 1
    assert compare_runs({**a, "death_source_id": None}, {**a, "death_source_id": None}) == 0  # same progress


def test_hold_stats_count_only_ship_ticks():
    ticks = pd.DataFrame({"mode": ["cube"] * 4 + ["ship"] * 8 + ["cube"] * 2 + ["ship"] * 4,
                          "held": [1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1]})
    s = hold_stats(ticks)
    assert s["ticks"] == 12 and s["held_share"] == pytest.approx(7 / 12)
    # Ship stretches: [1 1 0 0 0 1 1 1] and [1 0 0 1]: holds 2, 3, 1, 1; releases 3, 2.
    assert s["holds"] == 4 and s["median_hold_ticks"] == 1.5 and s["median_release_ticks"] == 2.5
    assert s["switches_per_s"] == pytest.approx(4 / (12 / 240))  # 2 switches in each stretch
    assert hold_stats(ticks.assign(mode="cube"))["held_share"] is None


def test_sections_and_death_mode():
    level = mixed_level()
    sec = sections_reached(level, final_x=800, completed=False)
    assert sec == [{"x0": 400, "x1": 1200, "reached": True, "passed": False}]
    assert sections_reached(level, 0, True)[0]["passed"]
    ticks = pd.DataFrame({"mode": ["cube", "ship"], "held": [0, 1]})
    assert death_mode(ticks, False) == "ship" and death_mode(ticks, True) is None
