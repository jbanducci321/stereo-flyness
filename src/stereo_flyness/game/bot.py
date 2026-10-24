"""Search bot (Step 1.2): finds a button sequence that beats a level, or reports where it can't.

The bot plays through the same `Game.tick(held)` interface as everything else. It decides once per
frame (4 ticks by default): hold or release for the next frame. It tries "release" first, then
"hold", depth-first. When both choices from a state lead only to deaths, it rewinds
(`Game.snapshot`/`restore`) and tries the other branch further back.

States that have already been fully explored and failed are remembered, so each distinct state is
expanded once. For the cube, holding vs releasing in mid-air often leads to the same state, and
that merging is what keeps the search small.

If no path exists, the result reports the farthest point any branch reached and what killed the
branches there. A level that can't be beaten in our engine points at a physics or conversion gap.
"""

from collections import Counter
from dataclasses import dataclass, field

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.game.recorder import RunLog, play

CHOICES = (False, True)  # release first: the bot prefers not to press


@dataclass
class BotResult:
    success: bool
    frame_inputs: list[bool]  # winning per-frame choices (empty if no path was found)
    frame_ticks: int
    nodes: int  # states expanded
    farthest_x: float  # farthest x any branch reached
    stuck: Counter = field(default_factory=Counter)  # (kind, source_id, x) of deaths near farthest_x
    budget_exhausted: bool = False

    @property
    def tick_inputs(self) -> list[bool]:
        return [held for held in self.frame_inputs for _ in range(self.frame_ticks)]


def _key(game: Game) -> tuple:
    """Everything that affects the rest of the run (positions rounded to absorb float noise)."""
    p = game.player
    return (game.ticks, round(p.x, 6), round(p.y, 6), round(p.vy, 6), p.on_ground, p.mode,
            game.bounds, game._next_portal, id(game._snapped_to), round(game._snap_offset, 6))


def search(level: Level, frame_ticks: int = 4, max_nodes: int = 2_000_000, key=_key) -> BotResult:
    game = Game(level)
    stack = [[game.snapshot(), 0]]  # [state at the start of a frame, next choice index]
    path: list[bool] = []  # choice that led to each stack entry after the first
    failed: set = set()
    nodes, farthest_x, deaths = 0, 0.0, []

    while stack:
        top = stack[-1]
        if top[1] == len(CHOICES):  # every choice from this state fails
            stack.pop()
            failed.add(top[2] if len(top) > 2 else None)
            if path:
                path.pop()
            continue
        held = CHOICES[top[1]]
        top[1] += 1
        game.restore(top[0])
        for _ in range(frame_ticks):
            game.tick(held)
            if game.over:
                break
        nodes += 1
        farthest_x = max(farthest_x, game.player.x)
        if game.finished:
            return BotResult(True, path + [held], frame_ticks, nodes, farthest_x)
        if game.death is not None:
            d = game.death
            deaths.append((d.kind, d.source_id, round(d.x)))
            continue
        k = key(game)
        if k in failed:
            continue
        if nodes >= max_nodes:
            return _failure(frame_ticks, nodes, farthest_x, deaths, budget_exhausted=True)
        path.append(held)
        stack.append([game.snapshot(), 0, k])

    return _failure(frame_ticks, nodes, farthest_x, deaths)


def _failure(frame_ticks, nodes, farthest_x, deaths, budget_exhausted=False) -> BotResult:
    near = Counter(d for d in deaths if d[2] >= farthest_x - 150)  # within 5 blocks of the farthest point
    return BotResult(False, [], frame_ticks, nodes, farthest_x, near, budget_exhausted)


def replay(level: Level, result: BotResult) -> RunLog:
    """Play the bot's winning inputs through a fresh game and log every tick."""
    inputs = iter(result.tick_inputs)
    return play(Game(level), lambda g: next(inputs, False))
