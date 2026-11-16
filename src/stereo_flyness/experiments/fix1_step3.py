"""Fix 1, step 3: reading the fly's runs on the iteration-2 training levels (docs/notes/fix1_step3_plan.md).

Pure functions; `scripts/fix1_step3_report.py` loads the runs, checks them and writes the report.

- **The feature** of a level is its first fix-case drop (`platform_drop (fix)` / `step_down_pits (fix)`).
- **A run gets past it** if the cube passes the drop's far edge alive (the group's outcome is "cleared").
- **A level gets past it** if at least half its seeds do (2 of 3).
- **Main measure:** levels where the fixed fly gets past and the unfixed one doesn't, against the
  reverse; a two-sided sign test over those levels. Descriptive on training levels (D55's bar is the
  held-out suite).
"""

from dataclasses import dataclass
from math import comb

from stereo_flyness.experiments.obstacles import Group, outcomes
from stereo_flyness.game.engine import Game

PLAIN = ("platform", "platform (2-high)")  # plain step-downs: platforms ending on plain ground


def is_fix_case(g: Group) -> bool:
    return g.type.endswith("(fix)")


def feature_index(gs: list[Group]) -> int | None:
    """The level's feature: its first fix-case drop, or None if it has none."""
    return next((i for i, g in enumerate(gs) if is_fix_case(g)), None)


def drop_k(g: Group) -> int:
    """Empty ground cells between the drop's last block before the pits and its first pit."""
    pits = sorted(b.x0 for b in g.boxes if b.kind == "pit")
    edge = max(b.x1 for b in g.boxes if b.kind == "block" and b.x1 < pits[0])
    return round((pits[0] - 10.5 - edge) / 30)  # a pit's hitbox starts 10.5 into its cell


def replay_jumps(level, held) -> tuple[Game, list[float]]:
    """Replay the logged holds; returns the game and the x of every jump (take-off tick)."""
    game, jumps = Game(level), []
    for h in held:
        if game.over:
            raise ValueError(f"{level.name}: the logged holds go on after the game ended")
        game.tick(bool(h))
        if "jump" in game.events:
            jumps.append(game.player.x)
    return game, jumps


@dataclass
class RunReading:
    feature: int | None  # index of the level's first fix-case drop
    past: bool | None  # got past it (None if the level has none)
    outs: list[str]  # per group: cleared / died / not reached
    plain_reached: int  # plain step-downs reached
    plain_jumps: int  # jumps taken while on top of one


def read_run(gs: list[Group], completed: bool, death_x: float | None, jumps: list[float]) -> RunReading:
    outs = outcomes(gs, completed, death_x)
    f = feature_index(gs)
    plain = [g for g, o in zip(gs, outs) if g.type in PLAIN and o != "not reached"]
    on_plain = sum(1 for x in jumps for g in plain if g.x0 + 15 <= x <= g.x1 + 15)
    return RunReading(f, None if f is None else outs[f] == "cleared", outs, len(plain), on_plain)


def level_past(pasts: list[bool]) -> bool:
    """A level gets past its feature if at least half its seeds do (the median run)."""
    return 2 * sum(pasts) >= len(pasts)


def sign_test(better: int, worse: int) -> float:
    """Two-sided exact sign test over the levels that differ (ties left out)."""
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
