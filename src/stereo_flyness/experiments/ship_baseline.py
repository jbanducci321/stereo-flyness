"""The ship baseline's design-specific measures (D53, docs/notes/ship_analysis_plan.md). Used by
scripts/ship_report.py; design-independent measures are in `ship_analysis`.

- `classify_death`: the plan's death classes, decided in its order:
  (s) stuck; (a) unseen: the killing object was never the nearest surface in any of the 37
  directions before contact; (b) the encoding's limit: re-played from the tick it was first seen
  with the design's ideal ship (sign-only, no brain), the ideal ship dies on the same object too;
  (d↑)/(d↓) the fly's control: the ideal ship survives it, and on the death tick the fly was above
  or below where the ideal ship was; (u) anything the rules can't decide.
- `random_holds`: chance that holds as often and switches as often as the fly: alternating hold and
  release stretches drawn from the fly's own hold and release lengths.
- `input_output`, `release_sides`, `lags`, `tracking`: how the fly flies, from brain.parquet.
"""

import numpy as np
import pandas as pd

from stereo_flyness.game.engine import Game
from stereo_flyness.game.physics import TICKS_PER_SECOND
from stereo_flyness.interface.ship_encoding import ShipEncoder

NO_NEURONS = {t: {s: [] for s in ("right", "left")} for t in ("T4c", "T4d", "T5c", "T5d")}
CLASSES = ("s", "a", "b", "d_up", "d_down", "u")
IDEAL_TERMS = {"B": "B", "B90": "B", "C": "C"}  # B90 differs from B only in ω_full, which the sign ignores


def ideal_encoder(level, design: str) -> ShipEncoder:
    return ShipEncoder(level, NO_NEURONS, rate_hz=0.0, terms=IDEAL_TERMS[design])


def ideal_holds(enc: ShipEncoder, game: Game) -> bool:
    """The ideal ship's decision for the next tick: release on downward ω, otherwise hold."""
    return enc.encode(game.player, game.bounds).omega_deg >= 0


def killing_cell(enc: ShipEncoder, level, death):
    """The visual cell (merged column object, as the encoding sees it) of the box that killed."""
    hits = [b for b in level.boxes if b.kind == death.kind and not (
        death.x + 15 < b.x0 or b.x1 < death.x - 15 or death.y + 15 < b.y0 or b.y1 < death.y - 15)]
    if not hits:
        return None
    b = min(hits, key=lambda b: abs((b.x0 + b.x1) / 2 - death.x) + abs((b.y0 + b.y1) / 2 - death.y))
    cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
    for c in enc.cells:
        if abs(c.x0 - (cx - 15)) < 1e-6 and c.bottom - 1e-6 <= cy <= c.top + 1e-6:
            return c
    return None


def _replay(level, held, n: int) -> Game:
    game = Game(level)
    for h in held[:n]:
        game.tick(bool(h))
    return game


def classify_death(level, held, design: str, stuck: bool = False) -> tuple[str, dict]:
    """(class, detail) for a ship-level run that died. `held` is the run's logged holds."""
    game = _replay(level, held, len(held))
    death = game.death
    if death is None:
        raise ValueError("the run didn't die")
    if stuck:
        return "s", {}
    enc = ideal_encoder(level, design)
    cell = killing_cell(enc, level, death)
    if cell is None:
        return "u", {"why": "no matching object"}
    first, g = None, Game(level)
    for k, h in enumerate(held):
        if g.player.mode == "ship" and any(hit is not None and hit.cell is cell for hit in enc.seen(g.player, g.bounds)):
            first = k
            break
        g.tick(bool(h))
    if first is None:
        return "a", {"cell_x0": cell.x0}
    # The ideal ship takes over from the first tick it would decide after seeing the object.
    ideal = _replay(level, held, first)
    y_at_death = None
    while not ideal.over:
        ideal.tick(ideal_holds(enc, ideal))
        if ideal.ticks == death.tick:
            y_at_death = ideal.player.y
        if ideal.player.x > cell.x1 + 30:  # past the object
            break
    detail = {"cell_x0": cell.x0, "first_seen_tick": first}
    if ideal.death is not None and killing_cell(enc, level, ideal.death) is cell:
        return "b", detail
    if ideal.death is not None or y_at_death is None:
        return "u", {**detail, "why": "the ideal ship died elsewhere first, or ended before the death tick"}
    detail["fly_y"], detail["ideal_y"] = death.y, y_at_death
    return ("d_up" if death.y > y_at_death else "d_down"), detail


def lengths(held: np.ndarray) -> tuple[list[int], list[int]]:
    """Lengths of the hold stretches and release stretches in `held`."""
    held = np.asarray(held, bool)
    if not len(held):
        return [], []
    edges = np.flatnonzero(held[1:] != held[:-1]) + 1
    starts, ends = np.concatenate([[0], edges]), np.concatenate([edges, [len(held)]])
    holds = [int(e - s) for s, e in zip(starts, ends) if held[s]]
    rels = [int(e - s) for s, e in zip(starts, ends) if not held[s]]
    return holds, rels


def random_holds(hold_lengths, release_lengths, rng):
    """A no-brain player alternating hold and release stretches drawn from the given lengths, with
    a random first state. Returns `policy(game) -> bool`."""
    if not hold_lengths or not release_lengths:
        raise ValueError("need at least one hold and one release length")
    state = {"held": None, "left": 0}

    def draw():
        pool = hold_lengths if state["held"] else release_lengths
        state["left"] = int(pool[rng.integers(len(pool))])

    def policy(game):
        if state["held"] is None:
            state["held"] = bool(rng.integers(2))
            draw()
        elif state["left"] == 0:
            state["held"] = not state["held"]
            draw()
        state["left"] -= 1
        return state["held"]

    return policy


def _ship_rows(brain: pd.DataFrame) -> pd.DataFrame:
    return brain[brain["mode"] == "ship"] if "mode" in brain else brain


def signed_f(brain: pd.DataFrame) -> pd.Series:
    """f with a sign: + for downward motion (the "down" group), - for upward, 0 for none."""
    b = _ship_rows(brain)
    return b["f"].where(b["driven_group"] == "down", -b["f"]).where(b["driven_group"] != "none", 0.0)


BINS = (-1.0001, -0.5, -0.1, -1e-9, 1e-9, 0.1, 0.5, 1.0001)
BIN_LABELS = ("up, f > 0.5", "up, 0.1–0.5", "up, < 0.1", "none", "down, < 0.1", "down, 0.1–0.5", "down, f > 0.5")


def input_output(brain: pd.DataFrame) -> pd.DataFrame:
    """Mean DNp22 rate (Hz) per side in bins of the signed input f, and the number of ticks per bin."""
    b = _ship_rows(brain)
    binned = pd.cut(signed_f(brain), BINS, labels=BIN_LABELS)
    out = b.groupby(binned, observed=False).agg(
        ticks=("f", "size"),
        **{f"DNp22_{s} Hz": (f"spikes_DNp22_{s}", "mean") for s in ("R", "L")})
    for s in ("R", "L"):
        out[f"DNp22_{s} Hz"] *= TICKS_PER_SECOND
    return out


def release_sides(brain: pd.DataFrame) -> dict:
    """Of the frames that released (a DNp22 spike), the share from right only, left only, or both."""
    b = _ship_rows(brain)
    r, left = b["spikes_DNp22_R"] > 0, b["spikes_DNp22_L"] > 0
    n = int((r | left).sum())
    return {"releases": n, "right only": int((r & ~left).sum()), "left only": int((left & ~r).sum()),
            "both": int((r & left).sum())}


def lags(brain: pd.DataFrame) -> list[int]:
    """Ticks from the pooled motion turning downward to the next release (DNp22 spike)."""
    b = _ship_rows(brain).reset_index(drop=True)
    down = (b["driven_group"] == "down").to_numpy()
    spike = ((b["spikes_DNp22_R"] > 0) | (b["spikes_DNp22_L"] > 0)).to_numpy()
    onsets = np.flatnonzero(down & ~np.concatenate([[False], down[:-1]]))
    out = []
    for i in onsets:
        nxt = np.flatnonzero(spike[i:])
        if len(nxt):
            out.append(int(nxt[0]))
    return out


def tracking(brain: pd.DataFrame) -> dict:
    """How well the ship's vertical speed follows v_req, and its error to the target's centre each
    time a column is passed (the target column changes)."""
    b = _ship_rows(brain).reset_index(drop=True)
    has = b["target_dy"].notna()
    speed_err = (b.loc[has, "vy"] - b.loc[has, "v_req"]).abs()
    dx = b["target_dx"].to_numpy(float)
    passed = np.flatnonzero(np.nan_to_num(np.diff(dx), nan=0.0) > 30)  # the target jumps to the next column
    at_pass = b.loc[passed, "target_dy"].abs().dropna()
    return {"median |vy - v_req| (units/s)": float(speed_err.median()) if len(speed_err) else None,
            "columns passed": int(len(at_pass)),
            "median |error| at the column (units)": float(at_pass.median()) if len(at_pass) else None}
