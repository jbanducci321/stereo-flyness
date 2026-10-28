"""Ship-only and mixed level generators (D26). Short levels keep the bot validation fast."""

import pytest

from stereo_flyness.game.bot import replay
from stereo_flyness.game.generator import (
    EXIT_GAP, GRID, PORTAL_CLEARANCE, SHIP_CEILING, SHIP_FLOOR, SHIP_TIERS, UNITS_PER_SECOND,
    build_mixed, build_ship, generate,
)
from stereo_flyness.game.objects import KIND_SIZES

SHORT = 12.0  # seconds: enough for several chunks while keeping ship searches quick


def test_same_seed_same_level():
    for build in (build_ship, build_mixed):
        assert build(4, "medium").to_dict() == build(4, "medium").to_dict()
        assert build(5, "medium").to_dict() != build(4, "medium").to_dict()


@pytest.mark.parametrize("difficulty", list(SHIP_TIERS))
def test_ship_levels_are_beatable_and_stay_in_the_ship_area(difficulty):
    for seed in range(2):
        g = generate("ship", seed, difficulty, seconds=SHORT)
        lv = g.level
        assert lv.start_mode == "ship" and lv.portals == []
        assert {b.kind for b in lv.boxes} <= set(KIND_SIZES)
        assert all(SHIP_FLOOR - 5 <= b.y0 and b.y1 <= SHIP_CEILING + 5 for b in lv.boxes)
        assert replay(lv, g.bot).summary.completed


def test_ship_openings_shrink_with_difficulty():
    rows = [SHIP_TIERS[d].opening_rows for d in ("easy", "medium", "hard")]
    assert rows == sorted(rows, reverse=True) and rows[-1] * GRID >= 3 * GRID  # always > the 30-unit ship


def test_mixed_levels_alternate_modes_through_portals():
    lv = build_mixed(0, "medium", seconds=30)
    modes = [p.mode for p in lv.portals]
    assert modes and modes[0] == "ship" and modes[-1] == "cube"
    assert all(a != b for a, b in zip(modes, modes[1:]))  # strictly alternating


def test_portals_have_clear_zones_and_exits_are_funnelled():
    lv = build_mixed(1, "hard", seconds=30)
    clear = PORTAL_CLEARANCE * UNITS_PER_SECOND - GRID
    lo, hi = EXIT_GAP
    for p in lv.portals:
        near = [b for b in lv.boxes if abs((b.x0 + b.x1) / 2 - p.x) < clear]
        if p.mode == "ship":
            assert near == []  # nothing near the entry portal
        else:
            # Only the funnel wall itself is near the exit portal, and its opening covers rows lo..hi.
            assert {b.kind for b in near} == {"block"}
            assert all(abs((b.x0 + b.x1) / 2 - p.x) < 1 for b in near)
            ys = sorted((b.y0 + b.y1) / 2 for b in near)
            assert all(not (lo * GRID < y < hi * GRID) for y in ys)


def test_mixed_level_is_beatable_and_switches_both_ways():
    g = generate("mixed", 2, "easy", seconds=20)
    events = [e for row in replay(g.level, g.bot).to_frame().events for e in row.split(";") if e]
    assert events.count("portal_ship") >= 1 and events.count("portal_cube") >= 1
    assert events[-1] == "finish"
