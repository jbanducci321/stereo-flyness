import pytest

from stereo_flyness.game.level import Box, Level, Portal, ship_bounds
from stereo_flyness.game.objects import hitbox


def make_level():
    return Level(
        name="test",
        source="hand-made",
        length=900,
        boxes=[Box("spike", *hitbox("spike", 315, 15)), Box("block", *hitbox("block", 105, 15), source_id=1)],
        portals=[Portal("ship", 400, 165), Portal("cube", 700, 15)],
    )


def test_save_load_round_trip(tmp_path):
    level = make_level()
    level.save(tmp_path / "level.json")
    assert Level.load(tmp_path / "level.json") == level


def test_boxes_and_portals_are_sorted():
    level = make_level()
    assert [b.kind for b in level.boxes] == ["block", "spike"]
    assert [p.mode for p in level.portals] == ["ship", "cube"]


def test_hitbox_centred_and_rotated():
    assert hitbox("spike", 315, 15) == (312, 9, 318, 21)  # 6 x 12, centred
    assert hitbox("slab", 15, 53) == (0, 46, 30, 60)  # top flush with the cell top
    assert hitbox("spike", 0, 0, rotation=90) == (-6, -3, 6, 3)  # width and height swap
    assert hitbox("spike", 0, 0, rotation=180) == hitbox("spike", 0, 0)
    with pytest.raises(ValueError):
        hitbox("spike", 0, 0, rotation=45)


def test_ship_bounds_rule():
    assert ship_bounds(165) == (0, 300)  # low portal: floor is the ground
    assert ship_bounds(149) == (0, 300)
    assert ship_bounds(315) == (150, 450)  # world 405 -> centre 390 -> floor 240 (level 150)


def test_sections():
    level = make_level()
    assert level.sections() == [
        ("cube", 0, 400, None),
        ("ship", 400, 700, (0, 300)),
        ("cube", 700, 900, None),
    ]


@pytest.mark.parametrize(
    "bad",
    [
        lambda: Box("saw", 0, 0, 1, 1),
        lambda: Box("block", 0, 0, 0, 1),
        lambda: Portal("ufo", 0, 0),
        lambda: Level("x", "y", 10, start_mode="wave"),
    ],
)
def test_invalid_values_rejected(bad):
    with pytest.raises(ValueError):
        bad()


def test_unknown_format_version_rejected():
    d = make_level().to_dict()
    d["format_version"] = 99
    with pytest.raises(ValueError):
        Level.from_dict(d)
