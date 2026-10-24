"""Search bot on hand-made ship and mixed levels."""

import functools
import time

from stereo_flyness.game.bot import _key, replay, search, solve
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox


def obj(kind, x, y):
    return Box(kind, *hitbox(kind, x, y))


def wall_with_gap(x, gap_bottom, gap_top, floor=0, ceiling=300):
    """A column of blocks at x filling floor..ceiling except the gap (multiples of 30)."""
    return [obj("block", x, y + 15) for y in range(floor, ceiling, 30) if not gap_bottom <= y < gap_top]


def ship_level(*boxes, portals=(), length=3000):
    return Level("test", "hand-made", length, list(boxes), list(portals), start_mode="ship")


def assert_beaten(lv, max_seconds=30):
    t0 = time.perf_counter()
    result = solve(lv)
    assert result.success, f"stuck at x={result.farthest_x:.0f}: {result.stuck.most_common(3)}"
    assert time.perf_counter() - t0 < max_seconds
    assert replay(lv, result).summary.completed
    return result


def test_open_ship_area():
    assert_beaten(ship_level())


def test_zigzag_gaps():
    walls = []
    for i, (lo, hi) in enumerate([(150, 270), (30, 150), (180, 300), (0, 120), (120, 240)]):
        walls += wall_with_gap(600 + 300 * i, lo, hi)
    assert_beaten(ship_level(*walls))


def test_narrow_gap_two_blocks_tall():
    assert_beaten(ship_level(*wall_with_gap(900, 120, 180)))  # 60 units for a 30-unit ship


def test_spiked_floor_and_ceiling_corridor():
    pits = [obj("pit", 615 + 30 * k, 2) for k in range(40)]
    ceiling = [obj("spike", 615 + 30 * k, 285) for k in range(40)]  # hanging spikes, y 279-291
    assert_beaten(ship_level(*pits, *ceiling))


def test_closed_wall_is_reported_after_the_finer_recheck():
    # Proving "impossible" means trying every ship trajectory before the wall, which gets expensive
    # fast with distance (x=315 takes ~50 s), so the wall comes right after the start.
    result = solve(ship_level(*wall_with_gap(165, 0, 0)))  # no gap at all
    assert not result.success and result.merge_steps == (0.5, 0.1)  # re-checked with the finest step
    kinds = {kind for kind, _, _ in result.stuck}
    assert kinds == {"block"} and 110 < result.farthest_x < 180


def test_too_coarse_merging_gives_false_failures_and_solve_recovers():
    lv = ship_level(*wall_with_gap(900, 120, 180))  # beatable (see the narrow gap test)
    coarse = functools.partial(_key, ship_y_step=2.0, ship_vy_step=0.5)
    assert not search(lv, key=coarse).success  # merging 2-unit buckets wrongly says "impossible"
    result = solve(lv, steps=((2.0, 0.5), (1.0, 0.25)))
    assert result.success and result.merge_steps == (1.0, 0.25)


def test_mixed_cube_ship_cube():
    boxes = [obj("spike", 500, 15)]  # cube section
    boxes += wall_with_gap(1200, 180, 300) + wall_with_gap(1500, 0, 120)  # ship section
    boxes += [obj("spike", 2300, 15)]  # back to cube
    portals = [Portal("ship", 800, 45), Portal("cube", 1900, 45)]
    lv = Level("test", "hand-made", 2800, boxes, portals)
    result = assert_beaten(lv)
    events = [e for row in replay(lv, result).to_frame().events for e in row.split(";") if e]
    assert events.count("portal_ship") == 1 and events.count("portal_cube") == 1


def test_raised_ship_area():
    # Climb into a ship portal at the ceiling (y 285); the area moves up to 120-420 (level y).
    upper = wall_with_gap(1200, 330, 420, floor=120, ceiling=420)  # gap only in the raised part
    assert_beaten(ship_level(*upper, portals=[Portal("ship", 700, 285)], length=2000))
