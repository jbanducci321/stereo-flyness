import numpy as np
import pandas as pd
import pytest

from stereo_flyness.experiments.references import play
from stereo_flyness.experiments.ship_baseline import (
    classify_death, input_output, lags, lengths, random_holds, release_sides, tracking)
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level


def wall(x0, gap_bottom, gap_top, length=3000.0):
    boxes = [Box("block", x0, y, x0 + 30.0, y + 30.0) for y in range(0, 300, 30) if not gap_bottom <= y < gap_top]
    return Level("wall", "test", length, boxes, start_mode="ship")


def logged_holds(level, policy):
    game, held, out = Game(level), False, []
    while not game.over:
        game.tick(held)
        out.append(held)
        held = policy(game)
    return np.array(out, bool), game


def test_lengths_of_hold_and_release_stretches():
    assert lengths([1, 1, 0, 0, 0, 1]) == ([2, 1], [3])
    assert lengths([]) == ([], [])


def test_random_holds_alternate_with_the_given_lengths():
    rng = np.random.default_rng(0)
    pol = random_holds([4], [2], rng)
    seq = [pol(None) for _ in range(30)]
    holds, rels = lengths(seq)
    assert set(holds[1:-1]) == {4} and set(rels[1:-1]) == {2}


def test_never_hold_into_a_wall_with_a_gap_is_the_flys_fault_too_low():
    """The ideal B ship clears the gap, so a fly that stayed on the floor dies by its own control."""
    level = wall(600.0, 150, 240)  # gap 150-240, well above the floor
    held, game = logged_holds(level, lambda g: False)
    assert game.death is not None
    cls, detail = classify_death(level, held, "B")
    assert cls == "d_down" and detail["fly_y"] < detail["ideal_y"]


def test_a_closed_wall_is_the_encodings_limit():
    level = wall(600.0, 0, 0)  # no gap at all
    held, game = logged_holds(level, lambda g: False)
    assert classify_death(level, held, "B")[0] == "b"


def test_stuck_runs_are_class_s():
    level = wall(600.0, 0, 0)
    held, _ = logged_holds(level, lambda g: False)
    assert classify_death(level, held, "B", stuck=True)[0] == "s"


def test_a_completed_run_is_refused():
    level = Level("flat", "test", 300.0, [], start_mode="ship")
    held, game = logged_holds(level, lambda g: False)
    assert game.finished
    with pytest.raises(ValueError):
        classify_death(level, held, "B")


def brain(rows):
    return pd.DataFrame(rows, columns=["mode", "f", "driven_group", "spikes_DNp22_R", "spikes_DNp22_L",
                                       "vy", "v_req", "target_dy", "target_dx"])


def test_input_output_bins_and_rates():
    b = brain([("ship", 0.8, "down", 1, 0, 0, 0, None, None), ("ship", 0.8, "down", 1, 1, 0, 0, None, None),
               ("ship", 0.0, "none", 0, 0, 0, 0, None, None), ("ship", 0.3, "up", 0, 0, 0, 0, None, None)])
    io = input_output(b)
    assert io.loc["down, f > 0.5", "ticks"] == 2 and io.loc["down, f > 0.5", "DNp22_R Hz"] == pytest.approx(240.0)
    assert io.loc["down, f > 0.5", "DNp22_L Hz"] == pytest.approx(120.0)
    assert io.loc["none", "ticks"] == 1 and io.loc["up, 0.1–0.5", "DNp22_R Hz"] == 0.0


def test_release_sides_and_lags():
    b = brain([("ship", 0.0, "none", 0, 0, 0, 0, None, None), ("ship", 0.5, "down", 0, 0, 0, 0, None, None),
               ("ship", 0.5, "down", 0, 0, 0, 0, None, None), ("ship", 0.5, "down", 1, 0, 0, 0, None, None),
               ("ship", 0.5, "down", 1, 1, 0, 0, None, None)])
    assert release_sides(b) == {"releases": 2, "right only": 1, "left only": 0, "both": 1}
    assert lags(b) == [2]


def test_tracking_errors():
    b = brain([("ship", 0, "none", 0, 0, 100.0, 50.0, 20.0, 300.0), ("ship", 0, "none", 0, 0, 0.0, 50.0, 5.0, 30.0),
               ("ship", 0, "none", 0, 0, 0.0, 0.0, 40.0, 400.0)])
    t = tracking(b)
    assert t["median |vy - v_req| (units/s)"] == pytest.approx(50.0)
    assert t["columns passed"] == 1 and t["median |error| at the column (units)"] == pytest.approx(5.0)
