"""Stereo Madness on new seeds (D60): the report's measures, on generated levels only (hard rule 5)."""

from stereo_flyness.experiments import sm_newseeds as N
from stereo_flyness.experiments.stereo_madness import spread
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def _level(objs):
    return Level("t", "test", 4000.0, [Box(k, *hitbox(k, x, y)) for k, x, y in objs])


def test_the_strip_end_chains_hazards_a_cell_apart():
    lv = _level([("pit", 845, 2), ("pit", 875, 2), ("pit", 905, 2), ("pit", 1505, 2)])
    end = N.strip_end(lv, 870.0)
    assert end == max(b.x1 for b in lv.boxes if b.x0 < 1000)  # the three pits, not the lone one
    assert N.strip_end(lv, 1500.0) == max(b.x1 for b in lv.boxes)
    assert N.strip_end(lv, 1200.0) is None


def test_getting_past_needs_the_whole_cube_past_the_edge():
    assert not N.got_past(905.0, False, 900.0)  # centre past, body still over the pits
    assert N.got_past(916.0, False, 900.0)
    assert N.got_past(100.0, True, 900.0)


def test_milestones_count_runs():
    runs = [{"x": 950.0, "completed": False, "ship_reached": 0, "ship_passed": 0},
            {"x": 2500.0, "completed": False, "ship_reached": 1, "ship_passed": 0},
            {"x": 4000.0, "completed": True, "ship_reached": 2, "ship_passed": 2},
            {"x": 880.0, "completed": False, "ship_reached": 0, "ship_passed": 0}]
    assert N.milestones(runs, 900.0) == {"past Part 1's furthest point": 3, "reached the first ship portal": 2,
                                         "cleared the first ship section": 1, "completed the level": 1}


def test_the_median_of_100_is_the_mean_of_the_50th_and_51st():
    runs = [{"progress": p / 1000, "completed": False} for p in range(100)]  # 0.000 ... 0.099
    assert abs(spread(runs)["median"] - (0.049 + 0.050) / 2) < 1e-12


def test_prediction8_needs_the_band_and_a_run_past():
    assert N.prediction8(0.092, True)["hit"]
    assert N.prediction8(0.082, True)["hit"] and N.prediction8(0.102, True)["hit"]  # inclusive
    assert not N.prediction8(0.1021, True)["hit"]
    assert not N.prediction8(0.092, False)["hit"]


def test_seed_refused_only_part1_seeds():
    from stereo_flyness.experiments.sm_newseeds import FIRST_SEED, seed_refused
    assert FIRST_SEED == 100
    for seed in (0, 9, 10, 99):
        assert "seeds 0-99 are Part 1's" in seed_refused(seed)
    for seed in (100, 150, 199, 250):
        assert seed_refused(seed) is None
