"""A recorded run turned into per-tick data the viewer can draw.

Run logs (game/recorder.py) store the player's state each tick but not the ship area's
floor/ceiling. Those are rebuilt here from the level's portals and the logged portal events.
"""

import math
from dataclasses import dataclass

from stereo_flyness.game import physics as P
from stereo_flyness.game.level import Level, ship_bounds
from stereo_flyness.game.recorder import RunLog


@dataclass
class TickView:
    tick: int
    time: float
    x: float
    y: float
    mode: str
    held: bool
    events: tuple[str, ...]
    bounds: tuple[float, float] | None  # ship floor/ceiling, None in cube mode


class Timeline:
    """Per-tick view data for one run, starting with tick 0 (the start position)."""

    def __init__(self, level: Level, log: RunLog, driver: str | None = None):
        self.level = level
        self.summary = log.summary
        self.driver = driver  # "fly" or "bot" for brain runs (run.json); None for plain game runs
        df = log.to_frame()
        start_mode = level.start_mode
        start_y = P.HALF_PLAYER
        bounds = ship_bounds(start_y) if start_mode == "ship" else None
        self.ticks = [TickView(0, 0.0, 0.0, start_y, start_mode, False, (), bounds)]
        for row in df.itertuples(index=False):
            events = tuple(e for e in row.events.split(";") if e)
            if "portal_ship" in events:
                bounds = ship_bounds(self._portal_near(row.x, "ship").y)
            elif "portal_cube" in events:
                bounds = None
            self.ticks.append(TickView(int(row.tick), float(row.time), float(row.x), float(row.y),
                                       row.mode, bool(row.held), events, bounds))
        self.death_tick = next((t.tick for t in self.ticks if "death" in t.events), None)

    def _portal_near(self, x: float, mode: str):
        """The portal of `mode` the player was touching at `x` (the closest one by x)."""
        candidates = [p for p in self.level.portals if p.mode == mode]
        return min(candidates, key=lambda p: abs(p.x - x))

    @property
    def last_tick(self) -> int:
        return self.ticks[-1].tick

    @property
    def duration(self) -> float:
        return self.last_tick / P.TICKS_PER_SECOND

    def at_tick(self, tick: int) -> TickView:
        return self.ticks[max(0, min(tick, self.last_tick))]

    def at_time(self, seconds: float) -> TickView:
        return self.at_tick(math.floor(seconds * P.TICKS_PER_SECOND + 1e-9))
