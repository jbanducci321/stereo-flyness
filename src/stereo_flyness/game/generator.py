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

GENERATOR_VERSION = 3  # the newest version, used when none is asked for
# Every version still in use. The version is part of each level's random seed, so a level is fixed
# by (kind, difficulty, seed, version). Old suites keep their version: iteration 1's suites are v3
# and must rebuild unchanged (tests/test_generator_freeze.py). New chunks go behind a new version.
SUPPORTED_VERSIONS = (3, 4)
# v4 (iteration 2, docs/notes/iteration2_levels.md) changes **cube levels only**: it adds the
# platform_drop, step_down_pits, platform_step_down and spaced_pair chunks and guarantees every
# level one drop and one spaced pair. Ship and mixed levels keep the v3 chunks (with v4 seeds).
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
    # v4 cube chunks only (iteration2_levels.md):
    drop_heights: tuple[int, ...] = (1, 2)  # platform_drop / platform_step_down heights, in blocks
    pit_widths: tuple[int, int] = (2, 5)  # pit strip width after a drop, in cells
    pair_gaps: tuple[int, int] = (1, 4)  # empty cells between a spaced pair


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


# -- v4 cube chunks (iteration 2) ------------------------------------------------------

def _run(col: int, n: int, h: int) -> list[tuple[str, float, float]]:
    """A run of n columns of h stacked blocks, from column `col`."""
    return [("block", _col(col + i), 15 + GRID * j) for i in range(n) for j in range(h)]


def _pits_then(rng, tier, col: int, h: int) -> tuple[list[tuple[str, float, float]], int]:
    """k = 0-3 empty ground cells, a pit strip of the tier's widths, then plain ground or (50/50)
    a 3-5-cell landing platform of height h. Returns the objects and the next free column."""
    k, w = rng.randint(0, 3), rng.randint(*tier.pit_widths)
    col += k
    objs = [("pit", _col(col + i), 2) for i in range(w)]
    col += w
    if rng.random() < 0.5:
        m = rng.randint(3, 5)
        objs += _run(col, m, h)
        col += m
    return objs, col


def platform_drop(rng, tier):
    """A raised platform (1-2 blocks, 4-8 long), then pits: fix 1's case or its control."""
    h, n = rng.choice(tier.drop_heights), rng.randint(4, 8)
    objs = _run(0, n, h)
    rest, col = _pits_then(rng, tier, n, h)
    return objs + rest, GRID * col


def step_down_pits(rng, tier):
    """A 2-block run, then a 1-block run (each 2-4 long), then pits: the drop comes after a
    walk-off from a higher step, so the no-press path crosses two drops."""
    a, b = rng.randint(2, 4), rng.randint(2, 4)
    objs = _run(0, a, 2) + _run(a, b, 1)
    rest, col = _pits_then(rng, tier, a + b, 1)
    return objs + rest, GRID * col


def platform_step_down(rng, tier):
    """A raised platform (1-2 blocks, 4-8 long) ending on plain ground: the no-harm control."""
    h, n = rng.choice(tier.drop_heights), rng.randint(4, 8)
    return _run(0, n, h), GRID * n


def spaced_pair(rng, tier):
    """A spike, 1-4 empty cells, then a spike or (1 in 3) a block."""
    g = rng.randint(*tier.pair_gaps)
    second = "block" if rng.random() < 1 / 3 else "spike"
    return [("spike", _col(0), 15), (second, _col(g + 1), 15)], GRID * (g + 2)


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

CUBE_CHUNKS_V4: dict[str, Chunk] = {
    **CUBE_CHUNKS, "platform_drop": platform_drop, "step_down_pits": step_down_pits,
    "platform_step_down": platform_step_down, "spaced_pair": spaced_pair,
}


def _v4(tier: Tier, extra: dict[str, float], **ranges) -> Tier:
    """A v3 tier plus the new chunks, each about as frequent as that tier's platform chunk."""
    return Tier(tier.gap_seconds, {**tier.weights, **extra}, tier.opening_rows, tier.stair_width,
                tier.platform_spikes, **ranges)


_P = {d: t.weights["platform"] for d, t in CUBE_TIERS.items()}
CUBE_TIERS_V4 = {
    # Easy: 1-block drops only, so no step_down_pits (it has a 2-block step); narrower pits and gaps.
    "easy": _v4(CUBE_TIERS["easy"], {"platform_drop": _P["easy"], "platform_step_down": _P["easy"],
                                     "spaced_pair": _P["easy"]},
                drop_heights=(1,), pit_widths=(2, 3), pair_gaps=(2, 4)),
    "medium": _v4(CUBE_TIERS["medium"], {"platform_drop": _P["medium"], "step_down_pits": _P["medium"],
                                         "platform_step_down": _P["medium"], "spaced_pair": _P["medium"]},
                  pit_widths=(2, 4), pair_gaps=(1, 4)),
    "hard": _v4(CUBE_TIERS["hard"], {"platform_drop": _P["hard"], "step_down_pits": _P["hard"],
                                     "platform_step_down": _P["hard"], "spaced_pair": _P["hard"]},
                pit_widths=(2, 5), pair_gaps=(1, 4)),
}
GUARANTEE_WITHIN = 6  # v4: the guaranteed drop and spaced pair are among the first 6 chunks

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


def _assemble(rng, chunks: dict[str, Chunk], tier: Tier, x: float, x_end: float,
              forced: dict[int, str] | None = None) -> tuple[list[Box], float]:
    """Place random chunks from x until x_end. Returns the boxes and the x after the last gap.

    `forced` (v4 only) maps chunk positions to chunk names placed there instead of a random one;
    any not reached before x_end are placed after it, so they always appear. Without it, the
    random draws are exactly v3's."""
    names, weights = list(tier.weights), list(tier.weights.values())
    forced = dict(forced or {})
    boxes, i = [], 0
    while x < x_end or forced:
        if x >= x_end:  # past the end with guaranteed chunks still to place
            i = min(forced)
        name = forced.pop(i) if i in forced else rng.choices(names, weights)[0]
        objs, width = chunks[name](rng, tier)
        boxes += [Box(kind, *hitbox(kind, x + ox, oy)) for kind, ox, oy in objs]
        x = _snap(x + width + rng.uniform(*tier.gap_seconds) * UNITS_PER_SECOND)
        i += 1
    return boxes, x


def check_version(version: int) -> int:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"generator v{version} is not supported (supported: {SUPPORTED_VERSIONS})")
    return version


def _rng(kind: str, difficulty: str, seed: int, attempt: int, version: int) -> random.Random:
    return random.Random(f"{kind}:{check_version(version)}:{difficulty}:{seed}:{attempt}")


def _level(kind, difficulty, seed, attempt, version, length, boxes, portals=(), start_mode="cube") -> Level:
    return Level(
        name=f"{kind}-{difficulty}-{seed}",
        source=f"generator v{version}: {kind}, {difficulty}, seed {seed}, attempt {attempt}",
        length=length, boxes=boxes, portals=list(portals), start_mode=start_mode,
    )


def build_cube(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0,
               version: int = GENERATOR_VERSION) -> Level:
    """One candidate cube-only level (not yet checked by the bot)."""
    rng = _rng("cube", difficulty, seed, attempt, version)
    end = seconds * UNITS_PER_SECOND - END_RUNWAY  # obstacles stop so the level ends ~`seconds` in
    if version >= 4:
        tier = CUBE_TIERS_V4[difficulty]
        drops = [n for n in ("platform_drop", "step_down_pits") if n in tier.weights]
        slots = rng.sample(range(GUARANTEE_WITHIN), 2)
        forced = {slots[0]: rng.choice(drops), slots[1]: "spaced_pair"}
        boxes, x = _assemble(rng, CUBE_CHUNKS_V4, tier, START_RUNWAY, end, forced)
    else:
        boxes, x = _assemble(rng, CUBE_CHUNKS, CUBE_TIERS[difficulty], START_RUNWAY, end)
    return _level("cube", difficulty, seed, attempt, version, x + END_RUNWAY, boxes)


def build_ship(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0,
               version: int = GENERATOR_VERSION) -> Level:
    """One candidate ship-only level: starts as a ship in the ground-level area (floor 0, ceiling 300)."""
    rng = _rng("ship", difficulty, seed, attempt, version)
    end = seconds * UNITS_PER_SECOND - END_RUNWAY
    boxes, x = _assemble(rng, SHIP_CHUNKS, SHIP_TIERS[difficulty], START_RUNWAY, end)
    return _level("ship", difficulty, seed, attempt, version, x + END_RUNWAY, boxes, start_mode="ship")


def build_mixed(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0,
                section_seconds: tuple[float, float] = (6.0, 9.0), version: int = GENERATOR_VERSION) -> Level:
    """One candidate mixed level: cube and ship sections alternate, starting and ending with the cube.

    - **Into the ship:** a ship portal at ground level (centre y 45, touched by a cube on the
      ground), with PORTAL_CLEARANCE seconds of clear travel on each side.
    - **Back to the cube:** the cube portal sits in a funnel, a wall whose opening (rows 3-6,
      y 90-210) lies inside the portal's reach, so the ship can't fly past it. The opening is
      surrounded by clear travel.
    """
    rng = _rng("mixed", difficulty, seed, attempt, version)
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
    return _level("mixed", difficulty, seed, attempt, version, x + END_RUNWAY, boxes, portals)


BUILDERS = {"cube": build_cube, "ship": build_ship, "mixed": build_mixed}


@dataclass
class Generated:
    level: Level
    attempts: int  # how many candidates were tried (1 = the first was beatable)
    bot: BotResult  # the bot's winning run (replay it with bot.replay)
    rejected: list[str] = field(default_factory=list)  # sources of rejected candidates


def generate(kind: str, seed: int, difficulty: str = "medium", seconds: float = 30.0,
             validate: Callable = solve, version: int = GENERATOR_VERSION) -> Generated:
    """A bot-beatable level of `kind` ("cube", "ship" or "mixed"). Re-rolls until the bot beats one."""
    rejected = []
    for attempt in range(MAX_ATTEMPTS):
        level = BUILDERS[kind](seed, difficulty, seconds, attempt, version=version)
        result = validate(level)
        if result.success:
            return Generated(level, attempt + 1, result, rejected)
        rejected.append(level.source)
    raise RuntimeError(f"No beatable {kind} level for seed {seed} ({difficulty}) in {MAX_ATTEMPTS} attempts")


def generate_cube(seed: int, difficulty: str = "medium", seconds: float = 30.0,
                  validate: Callable = solve) -> Generated:
    return generate("cube", seed, difficulty, seconds, validate)
