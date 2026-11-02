"""Cube input encoding (D41) on hand-made levels with known geometry."""

import math

import numpy as np
import pytest

from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.player import Player
from stereo_flyness.interface.encoding import CubeEncoder, angular_size, obstacles

PATCHES = {"right": {"LC4": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "LPLC2": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]},
           "left": {"LC4": [21, 22, 23, 24, 25, 26, 27, 28, 29, 30], "LPLC2": [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]}}


def obj(kind, col, row=0):
    """An object in grid cell (col, row): centred at (30 col + 15, 30 row + 15), ground at y = 0."""
    return Box(kind, *hitbox(kind, 30 * col + 15, 30 * row + 15))


def level(*boxes):
    return Level("test", "test", 3000, list(boxes))


def encoder(lv, theta_full=180, mode="collision"):
    return CubeEncoder(lv, PATCHES, theta_full, 150, mode)


def on_ground(x):
    return Player(x=x)  # centre at y = 15, resting on the ground


def test_visual_cells_and_stacks():
    # A spike's hitbox is 6 x 12, but it fills its 30 x 30 cell; a two-block wall is one object
    obs = obstacles([obj("spike", 10), obj("block", 12), obj("block", 12, 1), obj("block", 12, 3)])
    assert [(o.x0, o.bottom, o.top) for o in obs] == [(300, 0, 30), (360, 0, 60), (360, 90, 120)]


def test_spike_at_the_calibrated_threshold():
    # Eye at the cell's centre height: theta = 2 atan(15 / d); 39 deg at d ~ 42.4
    d = 15 / math.tan(math.radians(19.5))
    eye_x = 300 - d
    loom = encoder(level(obj("spike", 10))).encode(on_ground(eye_x - 15))
    assert loom.theta_deg == pytest.approx(39.0, abs=1e-6)
    assert loom.gap == pytest.approx(d)


def test_taller_objects_look_bigger():
    spike = encoder(level(obj("spike", 10))).encode(on_ground(200)).theta_deg
    wall = encoder(level(obj("block", 10), obj("block", 10, 1))).encode(on_ground(200)).theta_deg
    expected = math.degrees(angular_size(300 - 215, 0, 60, 15))
    assert wall == pytest.approx(expected) and wall > spike


def test_nearest_looming_object_wins():
    enc = encoder(level(obj("spike", 20), obj("spike", 10)))
    assert enc.encode(on_ground(100)).obstacle.x0 == 300
    assert enc.encode(on_ground(300)).obstacle.x0 == 600  # past the first spike's front face


def test_only_collision_course_objects_loom():
    lv = level(obj("block", 10, 2))  # a ceiling block at y 60-90, above a cube on the ground
    assert encoder(lv).encode(on_ground(100)).obstacle is None
    assert encoder(lv).encode(on_ground(100)).theta_deg == 0
    # D43's comparison: every object ahead looms
    assert encoder(lv, mode="all").encode(on_ground(100)).obstacle.x0 == 300
    # Mid-jump, a spike below the cube stops looming
    airborne = Player(x=100, y=60, on_ground=False)
    assert encoder(level(obj("spike", 10))).encode(airborne).obstacle is None


def test_standing_on_a_platform_doesnt_loom():
    # The cube on top of a block row (y 30-60): the next block in the row is level with its feet
    lv = level(obj("block", 10), obj("block", 11), obj("spike", 15, 1))
    loom = encoder(lv).encode(Player(x=315, y=45))
    assert loom.obstacle.x0 == 450  # the spike on the platform, not the block underfoot


def test_patch_fraction_and_rates():
    # theta = 18 deg with theta_full = 180 drives 10% of each population on each side
    d = 15 / math.tan(math.radians(9))
    enc = encoder(level(obj("spike", 10)))
    loom = enc.encode(on_ground(300 - d - 15))
    assert loom.f == pytest.approx(0.1)
    assert set(loom.driven.values()) == {1}
    r = enc.rates(loom)
    assert r.sum() == 4 * 150 and len(r) == 40
    assert [enc.ids[i] for i in np.flatnonzero(r)] == [1, 11, 21, 31]  # the start of each patch order

    full = encoder(level(obj("spike", 10)), theta_full=10).encode(on_ground(200))
    assert full.f == 1.0 and set(full.driven.values()) == {10}



def test_rate_scaling_multiplies_r_by_f():
    # same 10% patch as above, but each driven neuron fires at R x f = 15 Hz
    d = 15 / math.tan(math.radians(9))
    enc = CubeEncoder(level(obj("spike", 10)), PATCHES, 180, 150, rate_scaling=True)
    loom = enc.encode(on_ground(300 - d - 15))
    assert loom.rate_hz == pytest.approx(15) and set(loom.driven.values()) == {1}
    r = enc.rates(loom)
    assert r.sum() == pytest.approx(4 * 15)
    full = CubeEncoder(level(obj("spike", 10)), PATCHES, 10, 150, rate_scaling=True).encode(on_ground(200))
    assert full.rate_hz == 150  # f = 1: the full rate

def test_nothing_ahead_and_ship_mode():
    enc = encoder(level(obj("spike", 10)))
    assert enc.encode(on_ground(400)).theta_deg == 0  # past everything
    ship = enc.encode(Player(x=100, mode="ship"))
    assert ship.obstacle is None and not enc.rates(ship).any()


def test_bad_settings_raise():
    with pytest.raises(ValueError, match="mode"):
        encoder(level(), mode="some")
    with pytest.raises(ValueError, match="theta_full"):
        encoder(level(), theta_full=0)


def test_cells_are_clipped_at_the_ground():
    # A pit spike whose cell spans -13 to 17 (Shannyn's case) is seen only above the floor
    pit = Box("spike", *hitbox("spike", 315, 2))
    (o,) = obstacles([pit])
    assert (o.bottom, o.top) == (0, 17)
    loom = encoder(level(pit)).encode(on_ground(300 - 26 - 15))  # gap 26
    assert loom.theta_deg == pytest.approx(math.degrees(angular_size(26, 0, 17, 15)))
    assert loom.theta_deg == pytest.approx(34.4, abs=0.1)  # ~51.5 deg before the clip
    # A cell entirely below the floor isn't seen at all
    assert obstacles([Box("spike", *hitbox("spike", 315, -20))]) == []
