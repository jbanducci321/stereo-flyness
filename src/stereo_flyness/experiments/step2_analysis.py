"""The Step 2 analysis (D48): death classes by replay, timing per approach, and paired comparisons.

A recorded fly-driven run is replayed exactly from its logged presses (the game is
deterministic), so every tick's state, nearest looming object and θ are rebuilt. From that:

- **Death classes, in D48's order:** (s) stuck, (a) invisible, (c) short run-up, (b) the ideal
  39° policy, taking over from the tick the killing object first loomed, dies before passing it
  too, (d) everything else, split at the first tick where the fly's and the ideal fly's
  **effective presses** (jumps) differ: (d1) the fly jumps there and the ideal fly doesn't, (d2)
  the ideal fly jumps there and the fly only jumps later, (d3) the fly never jumps.
- **Timing per approach** (D46's approaches): θ at the first Giant Fiber spike, the gap at the
  first jump (against the single-spike press window, gap 1-73), presses with nothing looming.
- **Paired comparisons:** per level better, worse or equal ("equal" = same killing object, or
  both completed), and a two-sided sign test with ties left out.

Nothing here picks or tunes anything: it reads runs that are already finished.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from stereo_flyness.experiments.subcircuit_validation import approaches
from stereo_flyness.game.engine import Game
from stereo_flyness.game.physics import HALF_PLAYER
from stereo_flyness.interface.encoding import CELL, CubeEncoder

THRESHOLD_DEG = 39.0  # the ideal fly's threshold (D43, D44)
MODEL_SD_DEG = 8.5  # s.d. of the calibrated model's first-spike θ (D43, D46)
LOOK_BACK_TICKS = 480  # (a) and (c) look at the last 2 s before death, as D44's death_cause
SPIKE_WINDOW = (1.0, 73.0)  # the single-spike press window, as the gap at the jump (docs/game_physics.md §3)
CLASSES = ("s", "a", "c", "b", "d1", "d2", "d3")


def killing_box(level, death):
    """The box that killed the cube: the nearest box of the death's kind within half a cell of
    where it died (the rule of D44's death_cause). None if nothing matches."""
    hits = [b for b in level.boxes if b.kind == death.kind and not (
        death.x + 15 < b.x0 or b.x1 < death.x - 15 or death.y + 15 < b.y0 or b.y1 < death.y - 15)]
    if not hits:
        return None
    return min(hits, key=lambda b: abs((b.x0 + b.x1) / 2 - death.x) + abs((b.y0 + b.y1) / 2 - death.y))


def cell_of(box) -> tuple[float, float]:
    """A box's visual cell: (front face x0, bottom)."""
    cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    return round(cx - CELL / 2, 6), round(cy - CELL / 2, 6)


def column_of(encoder: CubeEncoder, box):
    """The merged visual column (an encoder `Obstacle`) that contains this box's cell, if any."""
    x0, bottom = cell_of(box)
    mid = bottom + CELL / 2
    for o in encoder.obstacles:
        if abs(o.x0 - x0) < 1e-6 and o.bottom - 1e-6 <= mid <= o.top + 1e-6:
            return o
    return None


def object_of(encoder: CubeEncoder, box) -> tuple[float, float, float]:
    """The object a box belongs to, as (x0, bottom, top): its merged visual column, as the fly
    sees objects (a two-block wall is one object), or its own cell if it's never seen (below
    the floor). This is the identity behind "same killing object" (D48)."""
    o = column_of(encoder, box)
    if o is not None:
        return round(o.x0, 6), round(o.bottom, 6), round(o.top, 6)
    x0, bottom = cell_of(box)
    return x0, bottom, bottom + CELL


@dataclass
class Replay:
    """A run rebuilt tick by tick. Index k is the state before game tick k + 1 (what brain frame k saw)."""
    level: object
    encoder: CubeEncoder
    snapshots: list  # Game snapshots before each tick
    players: list  # Player state before each tick
    obstacle: list  # nearest looming obstacle before each tick (None if nothing looms)
    theta: np.ndarray  # its θ, degrees
    held: np.ndarray  # the logged press applied in each tick
    jumped: np.ndarray  # whether that press started a jump (an effective press)
    game: Game  # the game at the end of the replay


def replay(level, held, mode: str) -> Replay:
    """Replay a run from its logged presses. `mode` is the run's encoding mode (θ depends only on it)."""
    enc = CubeEncoder(level, {s: {t: [] for t in ("LC4", "LPLC2")} for s in ("right", "left")}, 180.0, 150.0, mode)
    game = Game(level)
    snaps, players, obs, theta, jumped = [], [], [], [], []
    for h in held:
        if game.over:
            raise ValueError("the logged presses go on after the game ended")
        o, th = enc.nearest(game.player)
        snaps.append(game.snapshot())
        players.append(snaps[-1].player)
        obs.append(o)
        theta.append(math.degrees(th))
        game.tick(bool(h))
        jumped.append("jump" in game.events)
    return Replay(level, enc, snaps, players, obs, np.array(theta), np.asarray(held, bool), np.array(jumped), game)


def check_replay(rep: Replay, run: dict, brain: pd.DataFrame | None = None) -> None:
    """Fail loudly if the replay doesn't rebuild the recorded run exactly."""
    g = rep.game
    if g.ticks != run["ticks"] or g.finished != run["completed"]:
        raise ValueError(f"replay of {run['level']} ends differently from the recording")
    if g.death is not None and (g.death.kind != run["death_kind"] or abs(g.death.x - run["death_x"]) > 1e-6):
        raise ValueError(f"replay of {run['level']} dies somewhere else than the recording")
    if brain is not None and not np.allclose(rep.theta, brain["theta_deg"].to_numpy(), atol=1e-6):
        raise ValueError(f"replay of {run['level']} doesn't see the θ the brain saw")


def ideal_press(encoder: CubeEncoder, player) -> bool:
    """The ideal fly's press for the tick after this state: θ ≥ 39° (D44)."""
    return player.mode == "cube" and math.degrees(encoder.nearest(player)[1]) >= THRESHOLD_DEG


def ideal_from(rep: Replay, start: int, far_edge: float) -> tuple[bool, object]:
    """From state `start`, the ideal 39° policy plays on. Returns (passed, death): passed is
    True if the cube's back edge gets past `far_edge` (or the level ends) before it dies."""
    game = Game(rep.level)
    game.restore(rep.snapshots[start])
    while not game.over:
        if game.player.x - HALF_PLAYER > far_edge:
            return True, None
        game.tick(ideal_press(rep.encoder, game.player))
    return game.finished, game.death


def classify_death(rep: Replay, stuck_at_death: bool) -> dict:
    """D48's death class for a run that died, with a short description of why."""
    game, level = rep.game, rep.level
    out = {"class": None, "killer": None, "killer_kind": None, "approach_start": None, "first_diff": None,
           "ideal_killer": None, "why": ""}
    if game.death is None:
        return out
    box = killing_box(level, game.death)
    if box is not None:
        out["killer"], out["killer_kind"] = object_of(rep.encoder, box), box.kind
    if stuck_at_death:
        return {**out, "class": "s", "why": "the stuck flag was on when it died"}
    column = None if box is None else column_of(rep.encoder, box)
    end = len(rep.held)
    window = range(max(0, end - LOOK_BACK_TICKS), end)
    seen = [k for k in window if column is not None and rep.obstacle[k] == column]
    if not seen:
        return {**out, "class": "a", "why": "never loomed before contact"}
    s = seen[0]
    out["approach_start"] = s
    if rep.theta[s] >= THRESHOLD_DEG:
        return {**out, "class": "c", "why": f"already {rep.theta[s]:.0f}° when it first loomed"}
    passed, death = ideal_from(rep, s, column.x1)
    if not passed:
        ideal_box = None if death is None else killing_box(level, death)
        ideal_killer = None if ideal_box is None else object_of(rep.encoder, ideal_box)
        same = ideal_killer == out["killer"]
        return {**out, "class": "b", "ideal_killer": ideal_killer,
                "why": "the ideal fly dies on it too" if same else "the ideal fly dies first on another object ("
                       + describe(None if ideal_box is None else ideal_box.kind, ideal_killer) + ")"}
    for k in range(s, end):
        ideal_jump = rep.players[k].on_ground and ideal_press(rep.encoder, rep.players[k])
        if bool(rep.jumped[k]) != bool(ideal_jump):
            out["first_diff"] = k
            if rep.jumped[k]:
                return {**out, "class": "d1", "why": f"jumped {k - s} ticks into the approach, before the ideal fly"}
            if rep.jumped[k + 1:end].any():
                return {**out, "class": "d2", "why": "jumped later than the ideal fly"}
            return {**out, "class": "d3", "why": "never jumped in the approach"}
    raise ValueError("the ideal fly passes but never jumps differently from the fly; the replay is wrong")


def describe(kind, obj) -> str:
    """A killing object for the report, e.g. "spike, object x 1230, y 0-30"."""
    if obj is None:
        return "unknown object"
    x0, bottom, top = obj
    return f"{kind}, object x {x0:.0f}, y {bottom:.0f}-{top:.0f}"


def isolated_ground_spike(level, encoder: CubeEncoder, obstacle) -> bool:
    """A lone spike on flat ground: a one-cell column at y 0-30 holding a spike, with no other
    object from one cell before it to four cells after it. Where D48's press window
    (gap 1-73) is known to apply."""
    if obstacle is None or abs(obstacle.bottom) > 1e-6 or abs(obstacle.top - CELL) > 1e-6:
        return False
    if not any(b.kind == "spike" and abs(cell_of(b)[0] - obstacle.x0) < 1e-6 for b in level.boxes):
        return False
    return not any(o is not obstacle and obstacle.x0 - CELL - 1e-6 <= o.x0 <= obstacle.x0 + 4 * CELL + 1e-6
                   for o in encoder.obstacles)


def approach_timing(rep: Replay, brain: pd.DataFrame) -> pd.DataFrame:
    """One row per obstacle approach (D46): θ at the first Giant Fiber spike in it, the gap at
    the first jump, and whether that jump is inside the single-spike window where it applies."""
    gf = (brain["spikes_GF_R"] + brain["spikes_GF_L"]).to_numpy() > 0
    gap = brain["gap"].to_numpy(float)
    stuck = brain["stuck_flag"].to_numpy(bool)
    rows = []
    for a, b in approaches(rep.theta, np.nan_to_num(gap, nan=0.0)):
        spikes = np.flatnonzero(gf[a:b])
        jumps = np.flatnonzero(rep.jumped[a:b])
        lone = isolated_ground_spike(rep.level, rep.encoder, rep.obstacle[a])
        jump_gap = gap[a + jumps[0]] if len(jumps) else None
        rows.append({"start": a, "ticks": b - a, "theta_start": rep.theta[a], "stuck": bool(stuck[a]),
                     "first_spike_theta": rep.theta[a + spikes[0]] if len(spikes) else None,
                     "jump_gap": jump_gap, "lone_spike": lone,
                     "in_window": None if not lone or jump_gap is None else
                     bool(SPIKE_WINDOW[0] <= jump_gap <= SPIKE_WINDOW[1])})
    return pd.DataFrame(rows)


def presses_nothing_looming(brain: pd.DataFrame) -> int:
    """Presses made in response to a frame where nothing loomed (should be ~0, D30)."""
    return int((brain["fly_press"].astype(bool) & (brain["theta_deg"] <= 0)).sum())


def compare(a: dict, b: dict) -> int:
    """+1 if run `a` did better than run `b`, -1 if worse, 0 if equal (D48): equal means both
    completed or both died on the same object; otherwise the one that got further is better."""
    if a["completed"] and b["completed"]:
        return 0
    if a["completed"] != b["completed"]:
        return 1 if a["completed"] else -1
    if a["killer"] is not None and a["killer"] == b["killer"]:
        return 0
    return int(np.sign(a["progress"] - b["progress"]))


def sign_test(better: int, worse: int) -> float:
    """Two-sided exact sign test, ties already left out. 1.0 with no untied pairs."""
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
