"""Procedural practice levels (Step 1.4, D26): seeded, physics-based, always bot-beatable.

A level is a run of obstacle "chunks" separated by flat gaps. Gap lengths are measured in seconds
of travel at normal speed, i.e. reaction time. Each difficulty tier sets the gap range, how often
each chunk appears and, for the ship, how wide its openings are.

Three kinds of level:
- **cube:** cube chunks only;
- **ship:** starts as a ship in the ground-level area (floor 0, ceiling 300), ship chunks only;
- **mixed:** alternating cube and ship sections joined by portals.

Rules:
- Difficulty comes from the physics (jump reach, reaction time, ship opening size), **never from
  Stereo Madness's layout** (D7). Nothing here reads or copies it.
- Only object kinds Stereo Madness uses (D6).
- Every level is checked by the search bot (D24). If the bot can't beat it, the level is re-rolled
  from the next attempt number, so a seed always maps to the same final, beatable level.
- Everything is placed on the 30-unit grid, as in GD.
"""

import random
from dataclasses import dataclass, field
from typing import Callable

from stereo_flyness.game import physics as P
from stereo_flyness.game.bot import BotResult, solve
from stereo_flyness.game.level import Box, Level, Portal, ship_bounds
from stereo_flyness.game.objects import hitbox

GENERATOR_VERSION = 3
GRID = 30.0
UNITS_PER_SECOND = P.X_PER_TICK * P.TICKS_PER_SECOND  # 311.58
START_RUNWAY = 600.0  # flat ground before the first obstacle (~1.9 s)
END_RUNWAY = 600.0
PORTAL_CLEARANCE = 1.0  # seconds of obstacle-free travel on each side of a portal
MAX_ATTEMPTS = 20

SHIP_FLOOR, SHIP_CEILING = ship_bounds(P.HALF_PLAYER)  # 0, 300: the ground-level ship area
SHIP_ROWS = int((SHIP_CEILING - SHIP_FLOOR) / GRID)  # 10 block rows
PORTAL_Y = 45.0  # portal centre for cube -> ship: touches a cube on the ground; area (0, 300)
EXIT_GAP = (3, 7)  # rows of the funnel opening around the ship -> cube portal (y 90-210)


@dataclass(frozen=True)
class Tier:
    gap_seconds: tuple[float, float]  # flat travel between chunks, in seconds
    weights: dict[str, float]  # relative frequency of each chunk
    opening_rows: int = 0  # ship only: height of openings, in 30-unit rows
    stair_width: int = 1  # cube only: width of each staircase step, in columns
    platform_spikes: bool = True  # cube only: platforms may carry a spike on top


# A chunk returns its objects as (kind, x, y) centres relative to the chunk's start, and its width.
Chunk = Callable[[random.Random, Tier], tuple[list[tuple[str, float, float]], float]]


def _col(i: int) -> float:
    """Centre x of the i-th grid column of a chunk."""
    return GRID * i + GRID / 2


def _row(j: int) -> float:
    """Centre y of the j-th grid row above the floor."""
    return SHIP_FLOOR + GRID * j + GRID / 2


# -- cube chunks -------------------------------------------------------------------

def spikes(n: int) -> Chunk:
    def chunk(rng, tier):
        return [("spike", _col(i), 15) for i in range(n)], GRID * n
    return chunk


def block(rng, tier):
    """One block on the ground: jump onto it or over it."""
    return [("block", _col(0), 15)], GRID


def stairs(rng, tier):
    """2-3 rising steps, one block higher each, with 3 empty columns between them.

    Steps are `tier.stair_width` columns wide. One-column pillars (hard tier only) need a precisely
    timed press to land on top. Their press window can drop to ~17-30 ms, shorter than the Giant
    Fiber's response (difficulty.py), so easier tiers use wider steps.
    """
    steps, w = rng.choice((2, 3)), tier.stair_width
    objs = [("block", _col(k * (w + 3) + c), 15 + GRID * j)
            for k in range(steps) for c in range(w) for j in range(k + 1)]
    return objs, GRID * ((steps - 1) * (w + 3) + w)


def platform(rng, tier):
    """A raised 1-block platform, 4-8 long, sometimes with a spike on top."""
    n = rng.randint(4, 8)
    objs = [("block", _col(i), 15) for i in range(n)]
    if tier.platform_spikes and n >= 6 and rng.random() < 0.5:
        objs.append(("spike", _col(rng.randint(3, n - 2)), 45))
    return objs, GRID * n


def slab_bridge(rng, tier):
    """Ground pits with a floating slab walkway above them (land on the slab, ride it across)."""
    n = rng.randint(4, 8)
    objs = [("pit", _col(i), 2) for i in range(n)] + [("slab", _col(i), 53) for i in range(n)]
    return objs, GRID * n


def slab_hops(rng, tier):
    """Ground pits with separate 2-slab platforms to hop between."""
    hops = rng.randint(2, 3)
    objs, col = [], 0
    for h in range(hops):
        objs += [("slab", _col(col), 53), ("slab", _col(col + 1), 53)]
        col += 2 + (rng.randint(2, 3) if h < hops - 1 else 0)
    objs += [("pit", _col(i), 2) for i in range(col)]
    return objs, GRID * col


CUBE_CHUNKS: dict[str, Chunk] = {
    "spike1": spikes(1), "spike2": spikes(2), "spike3": spikes(3), "block": block,
    "stairs": stairs, "platform": platform, "slab_bridge": slab_bridge, "slab_hops": slab_hops,
}

CUBE_TIERS = {
    # Easy leaves out staircases and platform spikes: both need sub-50 ms press timing (difficulty.py).
    "easy": Tier((0.9, 1.4), {"spike1": 5, "spike2": 2, "block": 3, "platform": 1},
                 stair_width=3, platform_spikes=False),
    "medium": Tier((0.6, 1.0), {"spike1": 3, "spike2": 3, "spike3": 1, "block": 2, "stairs": 2,
                                "platform": 2, "slab_bridge": 1}, stair_width=2),
    "hard": Tier((0.4, 0.7), {"spike1": 2, "spike2": 3, "spike3": 3, "block": 1, "stairs": 2,
                              "platform": 2, "slab_bridge": 2, "slab_hops": 2}, stair_width=1),
}

# -- ship chunks (ground-level area: floor 0, ceiling 300) ----------------------------


def _wall(col: int, gap_bottom: int, gap_rows: int) -> list[tuple[str, float, float]]:
    """A floor-to-ceiling column of blocks with an opening of `gap_rows` starting at row `gap_bottom`."""
    return [("block", _col(col), _row(j)) for j in range(SHIP_ROWS) if not gap_bottom <= j < gap_bottom + gap_rows]


def gap_wall(rng, tier):
    """A wall with one opening at a random height."""
    g = tier.opening_rows
    return _wall(0, rng.randint(0, SHIP_ROWS - g), g), GRID


def zigzag(rng, tier):
    """2-3 walls whose openings alternate between the lower and upper half."""
    g, n, objs, col = tier.opening_rows, rng.randint(2, 3), [], 0
    low = rng.random() < 0.5
    for k in range(n):
        half = (0, SHIP_ROWS // 2 - g // 2) if low else (SHIP_ROWS // 2 - g // 2, SHIP_ROWS - g)
        objs += _wall(col, rng.randint(*half), g)
        low = not low
        col += rng.randint(6, 8) if k < n - 1 else 1
    return objs, GRID * col


def spiked_corridor(rng, tier):
    """Pits on the floor and hanging spikes under the ceiling: stay off both."""
    n = rng.randint(6, 12)
    objs = [("pit", _col(i), SHIP_FLOOR + 2) for i in range(n)]
    objs += [("spike", _col(i), SHIP_CEILING - 15) for i in range(n)]
    return objs, GRID * n


def tunnel(rng, tier):
    """Walls above and below leaving an opening that drifts up or down by a row every few columns."""
    g, n = tier.opening_rows, rng.randint(6, 12)
    bottom, objs = rng.randint(1, SHIP_ROWS - g - 1), []
    for i in range(n):
        if i and i % 3 == 0:
            bottom = min(max(bottom + rng.choice((-1, 1)), 0), SHIP_ROWS - g)
        objs += _wall(i, bottom, g)
    return objs, GRID * n


def pillar(rng, tier):
    """A column rising from the floor or hanging from the ceiling, 3-6 blocks tall."""
    h = rng.randint(3, 6)
    rows = range(h) if rng.random() < 0.5 else range(SHIP_ROWS - h, SHIP_ROWS)
    return [("block", _col(0), _row(j)) for j in rows], GRID


SHIP_CHUNKS: dict[str, Chunk] = {
    "gap_wall": gap_wall, "zigzag": zigzag, "spiked_corridor": spiked_corridor,
    "tunnel": tunnel, "pillar": pillar,
}

SHIP_TIERS = {
    "easy": Tier((1.0, 1.5), {"gap_wall": 3, "pillar": 3, "spiked_corridor": 2, "zigzag": 1}, opening_rows=5),
    "medium": Tier((0.7, 1.1), {"gap_wall": 3, "pillar": 2, "spiked_corridor": 2, "zigzag": 2,
                                "tunnel": 1}, opening_rows=4),
    "hard": Tier((0.5, 0.8), {"gap_wall": 2, "pillar": 1, "spiked_corridor": 2, "zigzag": 3,
                              "tunnel": 3}, opening_rows=3),
}

# -- assembly ------------------------------------------------------------------------


def _snap(x: float) -> float:
    return round(x / GRID) * GRID


def _assemble(rng, chunks: dict[str, Chunk], tier: Tier, x: float, x_end: float) -> tuple[list[Box], float]:
    """Place random chunks from x until x_end. Returns the boxes and the x after the last gap."""
    names, weights = list(tier.weights), list(tier.weights.values())
    boxes = []
    while x < x_end:
        objs, width = chunks[rng.choices(names, weights)[0]](rng, tier)
        boxes += [Box(kind, *hitbox(kind, x + ox, oy)) for kind, ox, oy in objs]
        x = _snap(x + width + rng.uniform(*tier.gap_seconds) * UNITS_PER_SECOND)
    return boxes, x


def _rng(kind: str, difficulty: str, seed: int, attempt: int) -> random.Random:
    return random.Random(f"{kind}:{GENERATOR_VERSION}:{difficulty}:{seed}:{attempt}")


def _level(kind, difficulty, seed, attempt, length, boxes, portals=(), start_mode="cube") -> Level:
    return Level(
        name=f"{kind}-{difficulty}-{seed}",
        source=f"generator v{GENERATOR_VERSION}: {kind}, {difficulty}, seed {seed}, attempt {attempt}",
        length=length, boxes=boxes, portals=list(portals), start_mode=start_mode,
    )


def build_cube(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0) -> Level:
    """One candidate cube-only level (not yet checked by the bot)."""
    rng = _rng("cube", difficulty, seed, attempt)
    end = seconds * UNITS_PER_SECOND - END_RUNWAY  # obstacles stop so the level ends ~`seconds` in
    boxes, x = _assemble(rng, CUBE_CHUNKS, CUBE_TIERS[difficulty], START_RUNWAY, end)
    return _level("cube", difficulty, seed, attempt, x + END_RUNWAY, boxes)


def build_ship(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0) -> Level:
    """One candidate ship-only level: starts as a ship in the ground-level area (floor 0, ceiling 300)."""
    rng = _rng("ship", difficulty, seed, attempt)
    end = seconds * UNITS_PER_SECOND - END_RUNWAY
    boxes, x = _assemble(rng, SHIP_CHUNKS, SHIP_TIERS[difficulty], START_RUNWAY, end)
    return _level("ship", difficulty, seed, attempt, x + END_RUNWAY, boxes, start_mode="ship")


def build_mixed(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0,
                section_seconds: tuple[float, float] = (6.0, 9.0)) -> Level:
    """One candidate mixed level: cube and ship sections alternate, starting and ending with the cube.

    - **Into the ship:** a ship portal at ground level (centre y 45, touched by a cube on the
      ground), with PORTAL_CLEARANCE seconds of clear travel on each side.
    - **Back to the cube:** the cube portal sits in a funnel, a wall whose opening (rows 3-6,
      y 90-210) lies inside the portal's reach, so the ship can't fly past it. The opening is
      surrounded by clear travel.
    """
    rng = _rng("mixed", difficulty, seed, attempt)
    clear = PORTAL_CLEARANCE * UNITS_PER_SECOND
    total_end = seconds * UNITS_PER_SECOND - END_RUNWAY
    boxes, portals, x, mode = [], [], START_RUNWAY, "cube"
    while x < total_end:
        section_end = min(x + rng.uniform(*section_seconds) * UNITS_PER_SECOND, total_end)
        chunks, tier = (CUBE_CHUNKS, CUBE_TIERS[difficulty]) if mode == "cube" else (SHIP_CHUNKS, SHIP_TIERS[difficulty])
        new, x = _assemble(rng, chunks, tier, x, section_end)
        boxes += new
        if x >= total_end and mode == "cube":
            break
        x = _snap(x + clear)  # clear travel before the portal
        if mode == "cube":
            portals.append(Portal("ship", x + GRID / 2, PORTAL_Y))
            mode = "ship"
        else:
            lo, hi = EXIT_GAP
            boxes += [Box(k, *hitbox(k, x + ox, oy)) for k, ox, oy in _wall(0, lo, hi - lo)]
            portals.append(Portal("cube", x + GRID / 2, _row(lo) + (hi - lo - 1) * GRID / 2))
            mode = "cube"
        x = _snap(x + GRID + clear)  # clear travel after the portal
    return _level("mixed", difficulty, seed, attempt, x + END_RUNWAY, boxes, portals)


BUILDERS = {"cube": build_cube, "ship": build_ship, "mixed": build_mixed}


@dataclass
class Generated:
    level: Level
    attempts: int  # how many candidates were tried (1 = the first was beatable)
    bot: BotResult  # the bot's winning run (replay it with bot.replay)
    rejected: list[str] = field(default_factory=list)  # sources of rejected candidates


def generate(kind: str, seed: int, difficulty: str = "medium", seconds: float = 30.0,
             validate: Callable = solve) -> Generated:
    """A bot-beatable level of `kind` ("cube", "ship" or "mixed"). Re-rolls until the bot beats one."""
    rejected = []
    for attempt in range(MAX_ATTEMPTS):
        level = BUILDERS[kind](seed, difficulty, seconds, attempt)
        result = validate(level)
        if result.success:
            return Generated(level, attempt + 1, result, rejected)
        rejected.append(level.source)
    raise RuntimeError(f"No beatable {kind} level for seed {seed} ({difficulty}) in {MAX_ATTEMPTS} attempts")


def generate_cube(seed: int, difficulty: str = "medium", seconds: float = 30.0,
                  validate: Callable = solve) -> Generated:
    return generate("cube", seed, difficulty, seconds, validate)
