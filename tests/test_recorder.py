"""Run recording, summaries and replay (R1, D19)."""

from pathlib import Path

import pandas as pd
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.recorder import COLUMNS, RunLog, play

ROOT = Path(__file__).resolve().parents[1]
STEREO_MADNESS = ROOT / "data" / "gd" / "stereo_madness.json"


def level(*boxes, portals=(), length=3000):
    return Level("test", "hand-made", length, list(boxes), list(portals))


def spike(x):
    return Box("spike", *hitbox("spike", x, 15))


def test_death_is_recorded_tick_by_tick_and_summarised():
    log = play(Game(level(spike(615))), lambda g: False)
    s = log.summary
    assert not s.completed and s.death_kind == "spike" and s.jumps == 0
    assert len(log.rows) == s.ticks
    df = log.to_frame()
    assert list(df.columns) == COLUMNS
    assert df.tick.tolist() == list(range(1, s.ticks + 1))
    assert df.events.iloc[-1] == "death" and (df.events.iloc[:-1] == "").all()


def test_finish_is_recorded():
    log = play(Game(level(length=500)), lambda g: False)
    assert log.summary.completed and log.summary.progress == 1.0 and log.summary.death_kind is None
    assert log.to_frame().events.iloc[-1] == "finish"


def test_jump_land_and_portal_events():
    lv = level(portals=[Portal("ship", 1000, 45)])
    log = play(Game(lv), lambda g: g.ticks % 150 == 0, max_ticks=1000)  # press every 150 ticks
    events = [e for row in log.to_frame().events for e in row.split(";") if e]
    assert events.count("portal_ship") == 1
    jumps_before_portal = events[: events.index("portal_ship")]
    assert jumps_before_portal.count("jump") == jumps_before_portal.count("land") > 0
    assert log.summary.jumps == events.count("jump")


def test_save_and_load_round_trip(tmp_path):
    log = play(Game(level(spike(915))), lambda g: g.ticks % 97 == 0)
    log.save(tmp_path / "run")
    loaded = RunLog.load(tmp_path / "run")
    assert loaded.summary == log.summary
    pd.testing.assert_frame_equal(loaded.to_frame(), log.to_frame())


def test_replaying_the_logged_inputs_reproduces_the_run():
    lv = level(spike(915), Box("block", *hitbox("block", 1515, 15)))
    original = play(Game(lv), lambda g: g.ticks % 61 < 2)
    inputs = iter(original.to_frame().held.tolist())
    replay = play(Game(lv), lambda g: next(inputs))
    pd.testing.assert_frame_equal(replay.to_frame(), original.to_frame())
    assert replay.summary == original.summary


@pytest.mark.skipif(not STEREO_MADNESS.exists(), reason="Stereo Madness not built locally (D9)")
def test_engine_runs_stereo_madness_without_errors():
    """Smoke test only: trivial inputs die early. This checks the engine, not any tuning (D7)."""
    sm = Level.load(STEREO_MADNESS)
    for policy in (lambda g: False, lambda g: True):
        s = play(Game(sm), policy).summary
        assert not s.completed and s.death_kind is not None and s.progress < 0.05
