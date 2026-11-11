import pytest

from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.player import Player
from stereo_flyness.interface.encoding import Obstacle
from stereo_flyness.interface.ship_opening import Opening, OpeningFinder, openings

FLOOR, CEILING = 0.0, 300.0


def cell(bottom, top, x0=300.0):
    return Obstacle(x0, x0 + 30.0, bottom, top)


def block(x0, y0):
    return Box("block", x0, y0, x0 + 30.0, y0 + 30.0)


def ship(y, x=0.0):
    return Player(x=x, y=y, mode="ship", on_ground=False)


def test_an_empty_column_is_one_opening_floor_to_ceiling():
    assert openings([], FLOOR, CEILING) == [(0.0, 300.0)]


def test_a_wall_with_a_gap_leaves_the_gap():
    wall = [cell(0, 120), cell(210, 300)]
    assert openings(wall, FLOOR, CEILING) == [(120.0, 210.0)]


def test_gaps_smaller_than_the_ship_do_not_count():
    assert openings([cell(0, 100), cell(120, 300)], FLOOR, CEILING) == []
    assert openings([cell(0, 100), cell(130, 300)], FLOOR, CEILING) == [(100.0, 130.0)]  # exactly 30 fits


def test_cells_outside_the_ship_area_are_clipped():
    assert openings([cell(-60, 30), cell(270, 360)], FLOOR, CEILING) == [(30.0, 270.0)]


def level(*boxes):
    return Level("t", "test", 3000.0, list(boxes), start_mode="ship")


def test_the_target_is_the_opening_nearest_the_ship():
    # Column at x 300 (cells clipped at the ground): blocks fill 0-60 and 120-180, so openings 60-120 and 180-300.
    lv = level(block(300, 0), block(300, 30), block(300, 120), block(300, 150))
    o, err = OpeningFinder(lv).find(ship(100.0), (FLOOR, CEILING))
    assert o == Opening(300.0, 60.0, 120.0) and err == pytest.approx(-10.0)
    o, err = OpeningFinder(lv).find(ship(230.0), (FLOOR, CEILING))
    assert o == Opening(300.0, 180.0, 300.0) and err == pytest.approx(10.0)


def test_only_the_nearest_column_ahead_of_the_eye_within_range():
    lv = level(block(0, 0), block(300, 0), block(1100, 0))
    f = OpeningFinder(lv)
    assert f.next_column(45.0)[0] == 300.0  # ship's back at 30: the block at x 0-30 is fully passed
    assert f.next_column(385.0) is None  # passed 300 (back at 370); 1,100 is 700 from the eye: out of range
    assert f.next_column(505.0)[0] == 1100.0  # 580 from the eye: in range


def test_the_column_stays_the_target_while_the_ship_is_inside_its_gap():
    """Shannyn's §8a: no jumping ahead while the ship is still in the gap."""
    lv = level(block(300, 0), block(900, 0))
    f = OpeningFinder(lv)
    assert f.next_column(300.0)[0] == 300.0  # eye (315) past the front face, ship inside the column
    assert f.next_column(344.0)[0] == 300.0  # back edge at 329: not yet clear of 330
    assert f.next_column(346.0)[0] == 900.0  # back edge at 331: fully passed; 900 is 539 from the eye
    assert OpeningFinder(level()).find(ship(150.0), (FLOOR, CEILING)) == (None, None)


def test_a_closed_column_has_no_target():
    lv = level(*[block(300, y) for y in range(0, 300, 30)])
    assert OpeningFinder(lv).find(ship(150.0), (FLOOR, CEILING)) == (None, None)
