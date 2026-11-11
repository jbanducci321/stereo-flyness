"""Where the next opening is, for the ship: Shannyn's §8a (docs/notes/ship_proposals.md), used by
options B and C in `ship_encoding`.

What it computes, from the level's geometry only:
- **The next column:** the nearest column of visual cells (D41's 30 x 30 cells, clipped at the
  ground, D47) that the ship **hasn't fully passed** (its back face beyond the ship's back edge,
  x - 15), with its front face within `view_ahead` units of the eye (x + 15). So while the ship is
  inside a gap, that column stays the target.
- **Its openings:** the free vertical stretches between the ship area's floor and ceiling that no
  cell in that column covers, at least `min_gap` tall (default 30, the ship's hitbox).
- **The target:** the opening whose centre is nearest the ship's current height (ties go to the lower
  one), and the **error**: target centre minus the ship's y (positive = the opening is above).
"""

import bisect
from dataclasses import dataclass

from stereo_flyness.game.physics import PLAYER_SIZE
from stereo_flyness.interface.encoding import EYE_AHEAD, obstacles
from stereo_flyness.interface.ship_encoding import VIEW_AHEAD

_EPS = 1e-9


@dataclass(frozen=True)
class Opening:
    x0: float  # the column's front face
    bottom: float
    top: float

    @property
    def centre(self) -> float:
        return (self.bottom + self.top) / 2


def openings(column_cells, floor: float, ceiling: float, min_gap: float = PLAYER_SIZE) -> list[tuple[float, float]]:
    """Free (bottom, top) stretches between floor and ceiling not covered by `column_cells`
    (objects with .bottom and .top), at least `min_gap` tall, from the bottom up."""
    spans = sorted((max(c.bottom, floor), min(c.top, ceiling)) for c in column_cells if c.top > floor and c.bottom < ceiling)
    free, y = [], floor
    for b, t in spans:
        if b - y >= min_gap - _EPS:
            free.append((y, b))
        y = max(y, t)
    if ceiling - y >= min_gap - _EPS:
        free.append((y, ceiling))
    return free


class OpeningFinder:
    def __init__(self, level, view_ahead: float = VIEW_AHEAD, min_gap: float = PLAYER_SIZE):
        self.cells = obstacles(level.boxes)
        self._x0 = [c.x0 for c in self.cells]
        self.view_ahead, self.min_gap = view_ahead, min_gap

    def next_column(self, ship_x: float):
        """(front x, its cells) of the nearest column the ship (centre at `ship_x`) hasn't fully
        passed, with its front face within range of the eye, or None."""
        back, eye = ship_x - PLAYER_SIZE / 2, ship_x + EYE_AHEAD
        i = bisect.bisect_left(self._x0, back - PLAYER_SIZE - _EPS)  # cells are 30 wide
        while i < len(self.cells) and self.cells[i].x1 <= back + _EPS:
            i += 1
        if i == len(self.cells) or self.cells[i].x0 > eye + self.view_ahead + _EPS:
            return None
        x0 = self.cells[i].x0
        j = bisect.bisect_right(self._x0, x0 + _EPS)
        return x0, [c for c in self.cells[i:j] if c.x1 > back + _EPS]

    def find(self, player, bounds: tuple[float, float]) -> tuple[Opening | None, float | None]:
        """The target opening and the error (its centre minus the ship's y), or (None, None) when no
        column is in range or the next column has no opening the ship fits through."""
        col = self.next_column(player.x)
        if col is None:
            return None, None
        x0, cells = col
        free = openings(cells, bounds[0], bounds[1], self.min_gap)
        if not free:
            return None, None
        b, t = min(free, key=lambda s: (abs((s[0] + s[1]) / 2 - player.y), s[0]))
        o = Opening(x0, b, t)
        return o, o.centre - player.y
