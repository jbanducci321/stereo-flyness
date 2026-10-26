"""Procedural practice levels (Step 1.4, D26): seeded, physics-based, always bot-beatable.

A level is a run of obstacle "chunks" (single/double/triple spikes, a block, a staircase, a raised
platform, a slab bridge over pits...) separated by flat gaps. Gap lengths are measured in seconds
of travel at normal speed, i.e. reaction time. Each difficulty tier sets the gap range and how
often each chunk appears.

Rules:
- Difficulty comes from the physics (jump reach, reaction time), **never from Stereo Madness's
  layout** (D7). Nothing here reads or copies it.
- Only object kinds Stereo Madness uses (D6).
- Every level is checked by the search bot (D24). If the bot can't beat it, the level is re-rolled
  from the next attempt number, so a seed always maps to the same final, beatable level.
- Everything is placed on the 30-unit grid, as in GD.
"""

import random
from dataclasses import dataclass
from typing import Callable

from stereo_flyness.game import physics as P
from stereo_flyness.game.bot import solve
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox

GENERATOR_VERSION = 1
GRID = 30.0
UNITS_PER_SECOND = P.X_PER_TICK * P.TICKS_PER_SECOND  # 311.58
START_RUNWAY = 600.0  # flat ground before the first obstacle (~1.9 s)
END_RUNWAY = 600.0
MAX_ATTEMPTS = 20

# A chunk returns its objects as (kind, x, y) centres relative to the chunk's start, and its width.
Chunk = Callable[[random.Random], tuple[list[tuple[str, float, float]], float]]


def _col(i: int) -> float:
    """Centre x of the i-th grid column of a chunk."""
    return GRID * i + GRID / 2


def spikes(n: int) -> Chunk:
    def chunk(rng):
        return [("spike", _col(i), 15) for i in range(n)], GRID * n
    return chunk


def block(rng):
    """One block on the ground: jump onto it or over it."""
    return [("block", _col(0), 15)], GRID


def stairs(rng):
    """2-3 rising block columns, one block higher each, 4 columns apart (the standard step)."""
    steps = rng.choice((2, 3))
    objs = [("block", _col(4 * k), 15 + GRID * j) for k in range(steps) for j in range(k + 1)]
    return objs, GRID * (4 * (steps - 1) + 1)


def platform(rng):
    """A raised 1-block platform, 4-8 long, sometimes with a spike on top."""
    n = rng.randint(4, 8)
    objs = [("block", _col(i), 15) for i in range(n)]
    if n >= 6 and rng.random() < 0.5:
        objs.append(("spike", _col(rng.randint(3, n - 2)), 45))
    return objs, GRID * n


def slab_bridge(rng):
    """Ground pits with a floating slab walkway above them (land on the slab, ride it across)."""
    n = rng.randint(4, 8)
    objs = [("pit", _col(i), 2) for i in range(n)] + [("slab", _col(i), 53) for i in range(n)]
    return objs, GRID * n


def slab_hops(rng):
    """Ground pits with separate 2-slab platforms to hop between."""
    hops = rng.randint(2, 3)
    objs, col = [], 0
    for h in range(hops):
        objs += [("slab", _col(col), 53), ("slab", _col(col + 1), 53)]
        col += 2 + (rng.randint(2, 3) if h < hops - 1 else 0)
    objs += [("pit", _col(i), 2) for i in range(col)]
    return objs, GRID * col


CUBE_CHUNKS: dict[str, Chunk] = {
    "spike1": spikes(1),
    "spike2": spikes(2),
    "spike3": spikes(3),
    "block": block,
    "stairs": stairs,
    "platform": platform,
    "slab_bridge": slab_bridge,
    "slab_hops": slab_hops,
}


@dataclass(frozen=True)
class Tier:
    gap_seconds: tuple[float, float]  # flat ground between chunks, in seconds of travel
    weights: dict[str, float]  # relative frequency of each chunk


CUBE_TIERS = {
    "easy": Tier((0.9, 1.4), {"spike1": 5, "spike2": 2, "block": 3, "stairs": 1, "platform": 1}),
    "medium": Tier((0.6, 1.0), {"spike1": 3, "spike2": 3, "spike3": 1, "block": 2, "stairs": 2,
                                "platform": 2, "slab_bridge": 1}),
    "hard": Tier((0.4, 0.7), {"spike1": 2, "spike2": 3, "spike3": 3, "block": 1, "stairs": 2,
                              "platform": 2, "slab_bridge": 2, "slab_hops": 2}),
}


def _snap(x: float) -> float:
    return round(x / GRID) * GRID


def build_cube(seed: int, difficulty: str, seconds: float = 30.0, attempt: int = 0) -> Level:
    """One candidate cube-only level (not yet checked by the bot)."""
    tier = CUBE_TIERS[difficulty]
    rng = random.Random(f"cube:{GENERATOR_VERSION}:{difficulty}:{seed}:{attempt}")
    names, weights = list(tier.weights), list(tier.weights.values())
    end_of_obstacles = seconds * UNITS_PER_SECOND - END_RUNWAY  # the level ends ~`seconds` in
    boxes, x = [], START_RUNWAY
    while x < end_of_obstacles:
        objs, width = CUBE_CHUNKS[rng.choices(names, weights)[0]](rng)
        boxes += [Box(kind, *hitbox(kind, x + ox, oy)) for kind, ox, oy in objs]
        x = _snap(x + width + rng.uniform(*tier.gap_seconds) * UNITS_PER_SECOND)
    return Level(
        name=f"cube-{difficulty}-{seed}",
        source=f"generator v{GENERATOR_VERSION}: cube, {difficulty}, seed {seed}, attempt {attempt}",
        length=x + END_RUNWAY,
        boxes=boxes,
    )


@dataclass
class Generated:
    level: Level
    attempts: int  # how many candidates were tried (1 = the first was beatable)
    bot_nodes: int


def generate_cube(seed: int, difficulty: str = "medium", seconds: float = 30.0,
                  validate: Callable = solve) -> Generated:
    """A bot-beatable cube-only level. Re-rolls (attempt 1, 2, ...) until the bot beats one."""
    for attempt in range(MAX_ATTEMPTS):
        level = build_cube(seed, difficulty, seconds, attempt)
        result = validate(level)
        if result.success:
            return Generated(level, attempt + 1, result.nodes)
    raise RuntimeError(f"No beatable cube level for seed {seed} ({difficulty}) in {MAX_ATTEMPTS} attempts")
