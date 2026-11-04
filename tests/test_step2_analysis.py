import math

import numpy as np
import pytest

from stereo_flyness.experiments.step2_analysis import (
    THRESHOLD_DEG, approach_timing, classify_death, compare, ideal_press, replay, sign_test)
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def spike_level(x=600.0):
    return Level("one_spike", "test", x + 300, [Box("spike", *hitbox("spike", x, 15.0))])


def wall_level(x=600.0, cells=4):
    return Level("wall", "test", x + 300, [Box("block", *hitbox("block", x, 15.0 + 30 * i)) for i in range(cells)])


def play(level, press_at=()):
    """Presses on the listed ticks only; returns the presses up to the end of the game."""
    game, held = Game(level), []
    while not game.over:
        h = game.ticks in press_at
        held.append(h)
        game.tick(h)
    return held


def ideal_tick(level):
    """The first tick the ideal fly presses on, cube still on the ground."""
    rep = replay(level, play(level), "collision")
    return next(k for k, p in enumerate(rep.players) if ideal_press(rep.encoder, p))


def test_replay_rebuilds_the_run():
    level = spike_level()
    rep = replay(level, play(level), "collision")
    assert rep.game.death is not None and rep.game.death.kind == "spike"
    assert rep.theta.max() > THRESHOLD_DEG and not rep.jumped.any()


def test_never_jumping_at_a_spike_is_d3():
    level = spike_level()
    out = classify_death(replay(level, play(level), "collision"), stuck_at_death=False)
    assert out["class"] == "d3" and out["killer_kind"] == "spike"


def test_stuck_comes_first():
    level = spike_level()
    assert classify_death(replay(level, play(level), "collision"), stuck_at_death=True)["class"] == "s"


def test_jumping_too_early_is_d1():
    level = spike_level()
    k = ideal_tick(level)
    early = [t for t in range(k - 60, k) if replay(level, play(level, {t}), "collision").game.death is not None]
    rep = replay(level, play(level, {early[-1]}), "collision")
    out = classify_death(rep, stuck_at_death=False)
    assert out["class"] == "d1" and out["first_diff"] == early[-1]


def test_jumping_too_late_is_d2():
    level = spike_level()
    k = ideal_tick(level)
    late = [t for t in range(k + 1, k + 60) if replay(level, play(level, {t}), "collision").game.death is not None]
    out = classify_death(replay(level, play(level, {late[0]}), "collision"), stuck_at_death=False)
    assert out["class"] == "d2" and out["first_diff"] == k


def test_landing_on_a_hidden_second_spike_after_an_early_jump_is_d1():
    # Two spikes in a row: the second never looms (the first hides it), but the death was
    # decided on the first one, where the ideal fly would have jumped later and cleared both.
    level = Level("two_spikes", "test", 900, [Box("spike", *hitbox("spike", x, 15.0)) for x in (600.0, 630.0)])
    k = ideal_tick(level)
    assert replay(level, play(level, {k}), "collision").game.finished
    early = [t for t in range(k - 20, k) if (g := replay(level, play(level, {t}), "collision").game).death is not None
             and g.death.x > 600]
    rep = replay(level, play(level, {early[-1]}), "collision")
    out = classify_death(rep, stuck_at_death=False)
    assert out["killer"][0] == 615.0 and out["class"] == "d1"


def test_the_ideal_flys_own_killer_decides_a():
    # A row of spikes nobody can clear. The fly jumps later than the ideal fly and gets one spike
    # further; the ideal fly dies earlier, landing onto a spike that never loomed in its game: (a),
    # on a different object from the fly's killer (Shannyn, 2026-11-03).
    level = Level("row", "test", 1500, [Box("spike", *hitbox("spike", 600.0 + 30 * i, 15.0)) for i in range(12)])
    k = ideal_tick(level)
    for t in range(k, k + 40):
        out = classify_death(replay(level, play(level, {t}), "collision"), stuck_at_death=False)
        if out["killer"] != out["ideal_killer"]:
            break
    assert out["class"] == "a" and out["ideal_killer"] is not None and out["ideal_killer"] != out["killer"]


def test_a_wall_too_tall_to_jump_is_b():
    level = wall_level()
    out = classify_death(replay(level, play(level), "collision"), stuck_at_death=False)
    assert out["class"] == "b" and out["ideal_killer"] == out["killer"]


def test_a_completed_run_has_no_class():
    level = spike_level()
    rep = replay(level, play(level, {ideal_tick(level)}), "collision")
    assert rep.game.finished and classify_death(rep, False)["class"] is None


def test_approach_timing_finds_the_lone_spike_jump():
    import pandas as pd
    level = spike_level()
    k = ideal_tick(level)
    rep = replay(level, play(level, {k}), "collision")
    n = len(rep.held)
    gaps = [None if o is None else o.x0 - (p.x + 15) for o, p in zip(rep.obstacle, rep.players)]
    brain = pd.DataFrame({"theta_deg": rep.theta, "gap": gaps, "spikes_GF_R": np.eye(1, n, k - 1, dtype=int)[0],
                          "spikes_GF_L": 0, "stuck_flag": False, "fly_press": rep.held})
    t = approach_timing(rep, brain)
    assert len(t) == 1 and t["lone_spike"].iloc[0] and t["in_window"].iloc[0]
    assert t["first_spike_theta"].iloc[0] == pytest.approx(rep.theta[k - 1])


def test_compare_uses_the_killing_object():
    a = {"completed": False, "progress": 0.5, "killer": (585.0, 0.0, 30.0)}
    assert compare(a, {**a, "progress": 0.49}) == 0  # same object, a few ticks apart
    assert compare(a, {**a, "progress": 0.4, "killer": (285.0, 0.0, 30.0)}) == 1
    assert compare({**a, "completed": True}, a) == 1
    assert compare({**a, "completed": True}, {**a, "completed": True}) == 0


def test_sign_test():
    assert sign_test(0, 0) == 1.0
    assert sign_test(5, 0) == pytest.approx(2 / 32)
    assert sign_test(6, 0) == pytest.approx(2 / 64)
    assert sign_test(3, 3) == 1.0
    assert sign_test(9, 1) == pytest.approx(2 * 11 / 1024)
    assert math.isclose(sign_test(1, 9), sign_test(9, 1))
