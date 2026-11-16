"""Fix 1, step 3's reading (docs/notes/fix1_step3_plan.md): the feature, getting past it, the sign test."""

import pytest

from stereo_flyness.experiments import fix1_step3 as S
from stereo_flyness.experiments.obstacles import groups
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def _level(objs):
    return Level("t", "test", 3600.0, [Box(k, *hitbox(k, x, y)) for k, x, y in objs])


def _drop(x0, k, w=3, h=1):
    return ([("block", x0 + 30 * i + 15, 15 + 30 * j) for i in range(6) for j in range(h)]
            + [("pit", x0 + 180 + 30 * (k + i) + 15, 2) for i in range(w)])


def test_the_feature_is_the_first_fix_case_drop_and_k_is_measured():
    gs = groups(_level([("spike", 615, 15)] + _drop(1200, 3) + _drop(2100, 0)))
    assert [g.type for g in gs] == ["spike1", "platform_drop (control)", "platform_drop (fix)"]
    assert S.feature_index(gs) == 2 and [S.drop_k(g) for g in gs[1:]] == [3, 0]


def test_getting_past_the_feature():
    gs = groups(_level(_drop(600, 0) + [("spike", 2415, 15)]))
    assert S.read_run(gs, True, None, []).past
    assert not S.read_run(gs, False, 800.0, []).past  # died in the drop's pits
    assert S.read_run(gs, False, 2410.0, []).past  # got past, died later
    assert S.read_run(groups(_level([("spike", 615, 15)])), True, None, []).past is None  # no feature


def test_jumps_on_plain_step_downs_are_counted():
    gs = groups(_level([("block", 600 + 30 * i + 15, 15) for i in range(6)]))
    r = S.read_run(gs, True, None, [700.0, 1500.0])
    assert r.plain_reached == 1 and r.plain_jumps == 1


def test_level_past_is_the_median_run_and_the_sign_test_is_exact():
    assert S.level_past([True, True, False]) and not S.level_past([True, False, False])
    assert S.sign_test(0, 0) == 1.0
    assert S.sign_test(6, 0) == pytest.approx(2 / 64)
    assert S.sign_test(3, 3) == 1.0
