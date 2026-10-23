"""Our level format (D22, spec in docs/level_format.md).

A level is a list of gameplay hitboxes and portals, in GD units with the ground at y = 0. The
engine only needs rectangle overlap tests: hitbox sizes are resolved when a level is built,
not at runtime.
"""

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from stereo_flyness.game.objects import HAZARD_KINDS, SOLID_KINDS

FORMAT_VERSION = 1
MODES = {"cube", "ship"}
SPEEDS = {"normal"}

# World y of the ground surface in GD (docs/game_physics.md §1, §10): world y = level y + 90.
GD_WORLD_Y_OFFSET = 90.0
SHIP_AREA_HEIGHT = 300.0  # 10 blocks


def ship_bounds(portal_y: float) -> tuple[float, float]:
    """Floor and ceiling (level y) of the ship area set by a ship portal at level y `portal_y`.

    GD rule (docs/game_physics.md §4): with the portal at world y, the area's centre is 240 if
    world y < 270, else world y rounded down to a multiple of 30. The area spans ±150 around it.
    """
    world_y = portal_y + GD_WORLD_Y_OFFSET
    centre = 240.0 if world_y < 270 else math.floor(world_y / 30.0) * 30.0
    floor = centre - SHIP_AREA_HEIGHT / 2 - GD_WORLD_Y_OFFSET
    return floor, floor + SHIP_AREA_HEIGHT


@dataclass(frozen=True)
class Box:
    """One object's hitbox. Solids can be landed on; hazards kill on contact."""

    kind: str
    x0: float
    y0: float
    x1: float
    y1: float
    source_id: int | None = None  # original GD object ID, for traceability

    def __post_init__(self):
        if self.kind not in SOLID_KINDS | HAZARD_KINDS:
            raise ValueError(f"Unknown object kind: {self.kind!r}")
        if not (self.x0 < self.x1 and self.y0 < self.y1):
            raise ValueError(f"Empty or inverted hitbox: {self}")

    @property
    def solid(self) -> bool:
        return self.kind in SOLID_KINDS


@dataclass(frozen=True)
class Portal:
    """A game-mode portal. Ship bounds are derived from `y` with `ship_bounds`."""

    mode: str
    x: float
    y: float
    source_id: int | None = None

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"Unknown portal mode: {self.mode!r}")


@dataclass
class Level:
    name: str
    source: str
    length: float  # x where the level ends
    boxes: list[Box] = field(default_factory=list)
    portals: list[Portal] = field(default_factory=list)
    start_mode: str = "cube"
    speed: str = "normal"

    def __post_init__(self):
        if self.start_mode not in MODES:
            raise ValueError(f"Unknown start mode: {self.start_mode!r}")
        if self.speed not in SPEEDS:
            raise ValueError(f"Unsupported speed: {self.speed!r}")
        self.boxes.sort(key=lambda b: (b.x0, b.y0))
        self.portals.sort(key=lambda p: p.x)

    def to_dict(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "source": self.source,
            "start_mode": self.start_mode,
            "speed": self.speed,
            "length": self.length,
            "boxes": [asdict(b) for b in self.boxes],
            "portals": [asdict(p) for p in self.portals],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Level":
        if d.get("format_version") != FORMAT_VERSION:
            raise ValueError(f"Unsupported level format version: {d.get('format_version')}")
        return cls(
            name=d["name"],
            source=d["source"],
            length=d["length"],
            boxes=[Box(**b) for b in d["boxes"]],
            portals=[Portal(**p) for p in d["portals"]],
            start_mode=d["start_mode"],
            speed=d["speed"],
        )

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Level":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def sections(self) -> list[tuple[str, float, float, tuple[float, float] | None]]:
        """(mode, x_start, x_end, ship bounds or None) for each stretch between portals.

        A ship portal reached while already in ship mode starts a new section with new bounds.
        """
        out, mode, start, bounds = [], self.start_mode, 0.0, None
        for p in self.portals:
            out.append((mode, start, p.x, bounds))
            mode, start = p.mode, p.x
            bounds = ship_bounds(p.y) if p.mode == "ship" else None
        out.append((mode, start, self.length, bounds))
        return [s for s in out if s[2] > s[1]]
