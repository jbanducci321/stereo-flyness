"""The spread-aware ideal fly (fix 2's check): one threshold drawn per approach, from the fly's spread."""

from stereo_flyness.experiments.spread_fly import MIN_THRESHOLD, spread_fly
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.interface.encoding import CubeEncoder

NO_PATCHES = {s: {t: [] for t in ("LC4", "LPLC2")} for s in ("right", "left")}


def _level(objs, length=2400.0):
    return Level("t", "test", length, [Box(k, *hitbox(k, x, y)) for k, x, y in objs])


def _enc(level):
    return CubeEncoder(level, NO_PATCHES, 180.0, 150.0)


def test_one_draw_per_approach_and_none_for_the_second_column_of_a_block():
    # a 2-wide block (one approach: its second column continues it) and two single spikes
    level = _level([("block", 615, 15), ("block", 645, 15), ("spike", 1215, 15), ("spike", 1815, 15)])
    run = spread_fly(_enc(level), level, seed=0, mean=39.0, sd=0.0)
    assert [x for x, _ in run.thresholds] == [600.0, 1200.0, 1800.0]
    assert all(t == 39.0 for _, t in run.thresholds)


def test_draws_are_seeded_and_vary_between_seeds():
    level = _level([("spike", 615 + 300 * i, 15) for i in range(5)])
    a, b = spread_fly(_enc(level), level, seed=1), spread_fly(_enc(level), level, seed=1)
    c = spread_fly(_enc(level), level, seed=2)
    assert a.thresholds == b.thresholds and a.thresholds != c.thresholds


def test_zero_spread_matches_a_fixed_threshold_fly():
    """With s.d. 0 it is the fixed ideal fly: a double spike is cleared at 39°, not at 30°."""
    level = _level([("spike", 615, 15), ("spike", 645, 15)])
    assert spread_fly(_enc(level), level, seed=0, mean=39.0, sd=0.0).completed
    late, early = (spread_fly(_enc(level), level, seed=0, mean=m, sd=0.0) for m in (39.0, 30.0))
    assert late.completed and not early.completed and early.death_x is not None


def test_draws_are_floored():
    level = _level([("spike", 615, 15)])
    run = spread_fly(_enc(level), level, seed=0, mean=-50.0, sd=1.0)
    assert run.thresholds[0][1] == MIN_THRESHOLD
