"""Geometry Dash object facts used to build levels (docs/game_physics.md §5 and §10).

Maps GD object IDs to our object kinds and their hitbox sizes. Sizes are in GD units
(1 block = 30), centred on the object's position.
"""

# kind -> (width, height)
KIND_SIZES = {
    "block": (30.0, 30.0),
    "slab": (30.0, 14.0),
    "spike": (6.0, 12.0),
    "small_spike": (4.0, 7.6),
    "half_spike": (6.0, 5.6),
    "pit": (9.0, 10.8),
}
SOLID_KINDS = {"block", "slab"}
HAZARD_KINDS = {"spike", "small_spike", "half_spike", "pit"}

# GD object ID -> our kind (only IDs that appear in Stereo Madness; see §10)
GD_ID_TO_KIND = {
    **{i: "block" for i in (1, 2, 3, 4, 6, 7, 62, 65)},
    40: "slab",
    8: "spike",
    103: "small_spike",
    39: "half_spike",
    9: "pit",
}
GD_ID_TO_PORTAL = {12: "cube", 13: "ship"}


def hitbox(kind: str, x: float, y: float, rotation: float = 0.0) -> tuple[float, float, float, float]:
    """Axis-aligned hitbox (x0, y0, x1, y1) of an object centred at (x, y).

    A rotation of 90 or 270 degrees swaps width and height. Rotations that aren't multiples of
    90 degrees aren't used in our levels and are rejected.
    """
    if rotation % 90:
        raise ValueError(f"Unsupported rotation {rotation} for {kind}")
    w, h = KIND_SIZES[kind]
    if rotation % 180:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
