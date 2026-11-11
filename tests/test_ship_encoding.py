import math

import numpy as np
import pytest

from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.player import Player
from stereo_flyness.interface.encoding import Obstacle
from stereo_flyness.interface.ship_encoding import (
    ELEVATIONS_DEG, VX, VY_PER_UNIT, Hit, ShipEncoder, image_motion, look)

FLOOR, CEILING = 0.0, 300.0


def test_37_directions_from_straight_down_to_straight_up():
    assert len(ELEVATIONS_DEG) == 37
    assert ELEVATIONS_DEG[0] == -90 and ELEVATIONS_DEG[-1] == 90 and np.all(np.diff(ELEVATIONS_DEG) == 5)


def test_speeds_in_units_per_second():
    assert VX == pytest.approx(311.58, abs=0.01)
    assert VY_PER_UNIT == pytest.approx(54.0)


def test_shannyns_example_edge_150_below_and_150_ahead():
    """Her §1b: an edge 150 below and 150 ahead moves down at ~60°/s from forward flight alone."""
    self_part, flight = image_motion(Hit(150.0, -150.0, "cell"), vy=0.0)
    assert self_part == 0.0
    assert flight == pytest.approx(-59.5, abs=0.1)


def test_climbing_moves_what_is_ahead_down():
    self_part, _ = image_motion(Hit(100.0, 0.0, "cell"), vy=100.0)
    assert self_part == pytest.approx(-math.degrees(1.0))


def test_straight_down_and_up_always_see_floor_and_ceiling():
    hits = look(0.0, 100.0, FLOOR, CEILING, [])
    assert hits[0] == Hit(0.0, -100.0, "floor")
    assert hits[-1] == Hit(0.0, 200.0, "ceiling")
    assert hits[18] is None  # straight ahead, nothing there


def test_surfaces_count_only_within_600_ahead():
    hits = look(0.0, 100.0, FLOOR, CEILING, [])
    by = dict(zip(ELEVATIONS_DEG, hits))
    assert by[-45].what == "floor" and by[-45].d == pytest.approx(100.0)
    assert by[-10].d == pytest.approx(100 / math.tan(math.radians(10)))  # 567: in range
    assert by[-5] is None  # the floor is 1,143 ahead along this line: out of range
    assert by[20].what == "ceiling" and by[20].d == pytest.approx(200 / math.tan(math.radians(20)))


def test_a_cell_ahead_is_seen_before_the_floor_behind_it():
    cell = Obstacle(200.0, 230.0, 0.0, 120.0)
    by = dict(zip(ELEVATIONS_DEG, look(0.0, 100.0, FLOOR, CEILING, [cell])))
    assert by[0] == Hit(200.0, 0.0, "cell")
    assert by[5] == Hit(200.0, pytest.approx(200 * math.tan(math.radians(5))), "cell")  # its front face
    assert by[-30].what == "floor"  # the floor at 173 ahead is nearer than the cell
    assert by[10] is None  # passes over the cell (y 135 at x 200), and the ceiling is 1,134 ahead
    assert by[30].what == "ceiling"


def test_a_cell_overhead_hides_the_ceiling_straight_up():
    cell = Obstacle(-10.0, 20.0, 180.0, 210.0)
    assert look(0.0, 100.0, FLOOR, CEILING, [cell])[-1] == Hit(0.0, 80.0, "cell")


def test_the_eye_does_not_see_a_cell_it_is_inside_or_cells_behind_it():
    inside = Obstacle(-10.0, 20.0, 90.0, 120.0)
    behind = Obstacle(-60.0, -30.0, 0.0, 300.0)
    assert look(0.0, 100.0, FLOOR, CEILING, [inside, behind]) == look(0.0, 100.0, FLOOR, CEILING, [])


def test_flight_term_cancels_midway_between_floor_and_ceiling():
    """Floor and ceiling equally far: forward flight moves them equally down and up."""
    hits = look(0.0, 150.0, FLOOR, CEILING, [])
    flight = sum(image_motion(h, 0.0)[1] for h in hits if h is not None)
    assert flight == pytest.approx(0.0, abs=1e-9)


def neurons():
    ids = iter(range(1, 1000))
    return {t: {s: [next(ids) for _ in range(3)] for s in ("right", "left")} for t in ("T4c", "T4d", "T5c", "T5d")}


def encoder(terms="full", **kw):
    return ShipEncoder(Level("flat", "test", 3000.0, [], start_mode="ship"), neurons(), 150.0, terms=terms, **kw)


def ship(y, vy=0.0, x=0.0):
    return Player(x=x, y=y, vy=vy, mode="ship", on_ground=False)


def test_near_the_floor_flight_pulls_down_but_self_motion_alone_sees_nothing():
    """Shannyn's §1d worry: flying level just above the floor, the floor below streams downward."""
    m_full = encoder("full").encode(ship(30.0), (FLOOR, CEILING))
    m_self = encoder("self").encode(ship(30.0), (FLOOR, CEILING))
    assert m_full.omega_deg < 0 and m_full.group == "down" and m_full.omega_self_deg == 0.0
    assert m_self.omega_deg == 0.0 and m_self.group is None and m_self.rate_hz == 0.0


def test_climbing_drives_the_down_group_falling_the_up_group():
    up = encoder("self").encode(ship(150.0, vy=4.0), (FLOOR, CEILING))
    down = encoder("self").encode(ship(150.0, vy=-4.0), (FLOOR, CEILING))
    assert up.group == "down" and down.group == "up"
    assert up.omega_deg == pytest.approx(-down.omega_deg)


def test_rates_are_r_times_f_on_the_matching_group_only():
    enc = encoder("self", omega_full_deg=30.0)
    m = enc.encode(ship(150.0, vy=4.0), (FLOOR, CEILING))
    r = enc.rates(m)
    assert m.f == pytest.approx(min(1.0, abs(m.omega_deg) / 30.0))
    assert np.all(r["down"] == pytest.approx(150.0 * m.f)) and np.all(r["up"] == 0.0)
    fast = encoder("self", omega_full_deg=0.001).encode(ship(150.0, vy=4.0), (FLOOR, CEILING))
    assert fast.f == 1.0 and fast.rate_hz == 150.0


def test_groups_hold_both_eyes_or_one():
    both, right = encoder(), encoder(eyes=("right",))
    n = neurons()
    assert both.ids["down"] == n["T4d"]["right"] + n["T5d"]["right"] + n["T4d"]["left"] + n["T5d"]["left"]
    assert right.ids["up"] == n["T4c"]["right"] + n["T5c"]["right"]


def test_the_encoder_sees_the_level_cells():
    level = Level("one", "test", 3000.0, [Box("block", 300.0, 135.0, 330.0, 165.0)], start_mode="ship")
    m = ShipEncoder(level, neurons(), 150.0, terms="self").encode(ship(150.0, vy=4.0), (FLOOR, CEILING))
    m0 = encoder("self").encode(ship(150.0, vy=4.0), (FLOOR, CEILING))
    assert m.seen > m0.seen  # the block fills directions that saw nothing


def test_bad_settings_are_refused():
    with pytest.raises(ValueError):
        encoder(terms="flight")
    with pytest.raises(ValueError):
        encoder(omega_full_deg=0)


# Options B and C (Shannyn's §8)

def wall_level(gap_bottom, gap_top, x0=600.0):
    """A wall at x0 from floor to ceiling, with one gap."""
    boxes = [Box("block", x0, y, x0 + 30.0, y + 30.0) for y in range(0, 300, 30) if not gap_bottom <= y < gap_top]
    return Level("wall", "test", 3000.0, boxes, start_mode="ship")


def b_or_c(terms, lv):
    return ShipEncoder(lv, neurons(), 150.0, terms=terms)


def test_b_target_above_holds_target_below_releases():
    lv = wall_level(210, 270)  # gap centre 240
    up = b_or_c("B", lv).encode(ship(150.0), (FLOOR, CEILING))
    assert up.target_dy == pytest.approx(90.0) and up.v_req > 0 and up.group == "up"  # up: no release, hold
    down = b_or_c("B", wall_level(30, 90)).encode(ship(150.0), (FLOOR, CEILING))  # gap centre 60
    assert down.v_req < 0 and down.group == "down"


def test_v_req_reaches_the_target_by_the_column():
    m = b_or_c("C", wall_level(210, 270)).encode(ship(150.0), (FLOOR, CEILING))
    dx = 600.0 - 15.0
    assert m.dx == pytest.approx(dx)
    assert m.v_req == pytest.approx(90.0 * VX / dx)


def test_b_is_zero_when_moving_at_v_req_and_c_ignores_the_ships_motion():
    lv = wall_level(210, 270)
    v_req = b_or_c("B", lv).encode(ship(150.0), (FLOOR, CEILING)).v_req
    at = b_or_c("B", lv).encode(ship(150.0, vy=v_req / VY_PER_UNIT), (FLOOR, CEILING))
    assert at.omega_deg == pytest.approx(0.0, abs=1e-9)
    c0 = b_or_c("C", lv).encode(ship(150.0), (FLOOR, CEILING))
    c1 = b_or_c("C", lv).encode(ship(150.0, vy=5.0), (FLOOR, CEILING))
    assert c0.omega_deg == pytest.approx(c1.omega_deg) and c0.omega_deg == pytest.approx(-c0.omega_req_deg)


def test_b_without_a_target_is_self_motion_only():
    flat = Level("flat", "test", 3000.0, [], start_mode="ship")
    b = b_or_c("B", flat).encode(ship(150.0, vy=3.0), (FLOOR, CEILING))
    s = b_or_c("self", flat).encode(ship(150.0, vy=3.0), (FLOOR, CEILING))
    assert b.target_dy is None and b.v_req == 0.0 and b.omega_deg == pytest.approx(s.omega_deg)


def test_v_req_is_clipped_and_dx_is_at_least_30():
    m = b_or_c("C", wall_level(240, 300, x0=20.0)).encode(ship(30.0, x=0.0), (FLOOR, CEILING))  # inside the column's reach
    assert m.dx == 30.0 and m.v_req == pytest.approx(8.0 * VY_PER_UNIT)
