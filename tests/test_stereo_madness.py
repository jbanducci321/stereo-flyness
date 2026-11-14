"""Stereo Madness's report measures, on generated levels only (hard rule 5)."""

import pandas as pd
import pytest

from stereo_flyness.experiments.stereo_madness import cube_match, death_side, killing_box, showcase, spread, where
from stereo_flyness.game.engine import Death
from stereo_flyness.game.level import Box, Level, Portal


def level():
    # cube 0-1000, ship 1000-2000, cube 2000-3000, ship 3000-4000
    return Level("t", "test", 4000.0, [], portals=[Portal("ship", 1000.0, 45.0), Portal("cube", 2000.0, 15.0),
                                                   Portal("ship", 3000.0, 45.0)])


def test_where_a_run_ended_and_the_ship_sections_it_reached_and_passed():
    w = where(level(), 2500.0, completed=False)
    assert w["ended_in"] == "cube section 3 of 4" and w["ended_mode"] == "cube"
    assert (w["ship_sections"], w["ship_reached"], w["ship_passed"]) == (2, 1, 1)
    w = where(level(), 1500.0, completed=False)
    assert w["ended_mode"] == "ship" and (w["ship_reached"], w["ship_passed"]) == (1, 0)
    w = where(level(), 4000.0, completed=True)
    assert w["ended_in"] is None and (w["ship_reached"], w["ship_passed"]) == (2, 2)


def test_showcase_is_closest_to_the_median_with_ties_to_the_lowest_seed():
    runs = [{"seed": s, "progress": p} for s, p in enumerate([0.1, 0.4, 0.5, 0.6, 0.9])]
    assert showcase(runs)["seed"] == 2
    tie = [{"seed": 3, "progress": 0.4}, {"seed": 1, "progress": 0.6}]  # median 0.5: both 0.1 away
    assert showcase(tie)["seed"] == 1
    with pytest.raises(ValueError):
        showcase([])


def test_spread():
    s = spread([{"progress": p, "completed": p == 1.0} for p in (0.2, 0.4, 1.0, 0.6)])
    assert s["completed"] == 1 and s["runs"] == 4 and s["median"] == pytest.approx(0.5)
    assert (s["min"], s["max"]) == (0.2, 1.0)


def test_death_side_is_the_killing_box_against_the_player_centre():
    upper, spike = Box("block", 100.0, 110.0, 130.0, 140.0), Box("spike", 300.0, 0.0, 330.0, 30.0)
    lvl = Level("t", "test", 1000.0, [upper, spike])
    assert killing_box(lvl, Death("block", None, 110.0, 100.0, 5)) is upper
    assert death_side(lvl, Death("block", None, 110.0, 100.0, 5)) == "above"
    assert death_side(lvl, Death("spike", None, 310.0, 40.0, 9)) == "below"
    assert death_side(lvl, Death("spike", None, 600.0, 40.0, 9)) is None  # no box there
    assert death_side(lvl, None) is None


def ticks(modes, y):
    n = len(modes)
    return pd.DataFrame({"mode": modes, "x": [10.0 * i for i in range(n)], "y": y, "vy": [0.0] * n})


def test_cube_match_compares_every_tick_before_the_first_ship_tick():
    a = ticks(["cube"] * 3 + ["ship"] * 2, [15.0, 20.0, 25.0, 30.0, 35.0])
    b = ticks(["cube"] * 3 + ["ship"] * 2, [15.0, 20.0, 25.0, 99.0, 99.0])  # differs only in the ship
    assert cube_match(a, b) == {"identical": True, "ticks": 3, "first_diff": None}
    c = ticks(["cube"] * 5, [15.0, 20.0, 25.000001, 30.0, 35.0])  # exact equality, no tolerance
    assert cube_match(a, c) == {"identical": False, "ticks": 3, "first_diff": 2}
    d = ticks(["cube"] * 2, [15.0, 20.0])  # died a tick earlier, same states until then
    assert cube_match(a, d) == {"identical": False, "ticks": 2, "first_diff": 2}
    assert cube_match(d, d)["identical"]  # neither reaches a ship: compared to the end
