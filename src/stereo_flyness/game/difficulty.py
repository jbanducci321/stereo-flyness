"""How hard is a level? Measurements that tie level design to what the fly can do (D26).

- **Spacing:** obstacles are grouped into clusters (objects within one grid cell of each other).
  The flat gaps between clusters are converted to seconds of travel, i.e. reaction time.
- **Press windows (cube):** for each press in the bot's winning run, how far earlier or later the
  same press could have started (tick by tick) and still survived until the next press. The
  window's width, in ms, is directly comparable to the Giant Fiber's response latency
  (~35-50 ms in the model). For a single spike the window is ~238 ms (docs/game_physics.md §3).
- **Ship openings:** the smallest free vertical space the ship must pass through, column by
  column, inside the ship area.

Press windows are measured around the bot's particular path, so they describe the slack *along that
route*, not every possible route.
"""

import statistics
from dataclasses import dataclass

from stereo_flyness.game import physics as P
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level

GRID = 30.0
UNITS_PER_SECOND = P.X_PER_TICK * P.TICKS_PER_SECOND
MS_PER_TICK = 1000 / P.TICKS_PER_SECOND
MAX_SHIFT_TICKS = 90  # search +-375 ms around each press


@dataclass
class LevelStats:
    name: str
    seconds: float
    hazards: int
    solids: int
    clusters: int  # obstacle groups
    clusters_per_10s: float
    min_gap_s: float | None  # shortest flat travel between clusters
    median_gap_s: float | None
    presses: int  # cube presses in the bot's winning run
    tightest_window_ms: float | None  # smallest press window (cube)
    median_window_ms: float | None
    tightest_opening: float | None  # smallest passable vertical space in ship sections (units)
    windows_ms: list[float]


def clusters(level: Level) -> list[tuple[float, float]]:
    """(x_start, x_end) of each group of objects closer than one grid cell to each other."""
    out = []
    for b in level.boxes:  # sorted by x0
        if out and b.x0 <= out[-1][1] + GRID:
            out[-1] = (out[-1][0], max(out[-1][1], b.x1))
        else:
            out.append((b.x0, b.x1))
    return out


def _runs(inputs: list[bool]) -> list[tuple[int, int]]:
    """(start, end) tick indices of each contiguous held stretch (end exclusive)."""
    runs, start = [], None
    for i, held in enumerate(inputs + [False]):
        if held and start is None:
            start = i
        elif not held and start is not None:
            runs.append((start, i))
            start = None
    return runs


def press_windows(level: Level, tick_inputs: list[bool], max_shift: int = MAX_SHIFT_TICKS) -> list[float]:
    """Width (ms) of the timing window around each cube press in a winning input sequence.

    The window is the contiguous range of start shifts (in ticks, through 0) for which pressing
    that much earlier or later, all else unchanged, keeps the player alive until the next press
    (or the end of the level).
    """
    runs = _runs(tick_inputs)
    # Snapshots at each tick, from one replay of the winning inputs, to restart from quickly.
    game, snaps, modes = Game(level), [], []
    for held in tick_inputs:
        snaps.append(game.snapshot())
        modes.append(game.player.mode)
        game.tick(held)
    snaps.append(game.snapshot())

    windows = []
    for k, (start, end) in enumerate(runs):
        if modes[start] != "cube":
            continue
        lo_limit = runs[k - 1][1] + 1 if k else 0  # don't overlap the previous press
        horizon = runs[k + 1][0] if k + 1 < len(runs) else len(tick_inputs)
        hi_limit = horizon - (end - start) - 1  # nor run into the next one
        ok = {s: _survives(level, snaps, start + s, end - start, horizon, rewind_to=min(start, start + s))
              for s in range(max(-max_shift, lo_limit - start), min(max_shift, hi_limit - start) + 1)}
        width, s = 0, 0
        while ok.get(s):
            width, s = width + 1, s - 1
        s = 1
        while ok.get(s):
            width, s = width + 1, s + 1
        windows.append(width * MS_PER_TICK)
    return windows


def _survives(level, snaps, start: int, length: int, horizon: int, rewind_to: int) -> bool:
    """Press for `length` ticks from tick `start` (released otherwise); alive at `horizon`?

    Play resumes from `rewind_to`, which must be no later than the original press. Snapshots after
    it already contain the original jump.
    """
    game = Game(level)
    game.restore(snaps[rewind_to])
    for t in range(rewind_to, horizon):
        game.tick(start <= t < start + length)
        if game.death is not None:
            return False
        if game.finished:
            return True
    return True


def tightest_opening(level: Level) -> float | None:
    """Smallest 'largest free vertical gap' over all occupied grid columns of ship sections."""
    worst = None
    for mode, x0, x1, bounds in level.sections():
        if mode != "ship":
            continue
        floor, ceiling = bounds
        cols = {}
        for b in level.boxes:
            if b.x1 > x0 and b.x0 < x1:
                cols.setdefault(int(b.x0 // GRID), []).append((max(b.y0, floor), min(b.y1, ceiling)))
        for spans in cols.values():
            gap, y = 0.0, floor
            for lo, hi in sorted(spans):
                gap = max(gap, lo - y)
                y = max(y, hi)
            gap = max(gap, ceiling - y)
            worst = gap if worst is None else min(worst, gap)
    return worst


def measure(level: Level, tick_inputs: list[bool]) -> LevelStats:
    groups = clusters(level)
    gaps = [(b[0] - a[1]) / UNITS_PER_SECOND for a, b in zip(groups, groups[1:])]
    windows = press_windows(level, tick_inputs)
    seconds = level.length / UNITS_PER_SECOND
    return LevelStats(
        name=level.name, seconds=seconds,
        hazards=sum(not b.solid for b in level.boxes), solids=sum(b.solid for b in level.boxes),
        clusters=len(groups), clusters_per_10s=10 * len(groups) / seconds,
        min_gap_s=min(gaps, default=None), median_gap_s=statistics.median(gaps) if gaps else None,
        presses=len(windows),
        tightest_window_ms=min(windows, default=None),
        median_window_ms=statistics.median(windows) if windows else None,
        tightest_opening=tightest_opening(level), windows_ms=windows,
    )
