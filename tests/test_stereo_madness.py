"""Stereo Madness's report measures, on generated levels only (hard rule 5)."""

import pytest

from stereo_flyness.experiments.stereo_madness import showcase, spread, where
from stereo_flyness.game.level import Level, Portal


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
