"""The mixed-level check (Step 6, docs/notes/step6_proposal.md §5 step 2): before Stereo Madness, the
first runs where the brain switches between cube and ship at portals, to find a switching bug here
rather than in the one Stereo Madness batch. Used by scripts/mixed_check_report.py.

The switching checks, each computed from a run's logs (`play_modes`, D40's order):
- `mode_mismatches`: every brain row's mode is the mode the replayed game was in when that frame was
  shown (`tick_seen`), and rows are one per tick in order.
- `rule_mismatches`: every tick's press follows the rule of the mode the brain was shown: cube,
  either Giant Fiber spiked (D42); ship, released if either DNp22 spiked (D53). So the tick after a
  portal is still decided by the previous mode's rule, as designed.
- `encoding_mismatches`: a cube row logs the cube's encoding (θ) and no ship fields; a ship row the
  ship's (ω) and no cube fields.
- `input_rates`: how much each mode's input neurons fire while their mode is shown and while it
  isn't (described: an input left on in the wrong mode shows up as a high "not shown" rate).
"""

import numpy as np
import pandas as pd

from stereo_flyness.game.engine import Game
from stereo_flyness.game.physics import TICKS_PER_SECOND

CUBE_FIELD, SHIP_FIELD = "theta_deg", "omega_deg"


def shown_modes(level, held) -> list[str]:
    """The player's mode before each tick, replaying the logged holds."""
    game, out = Game(level), []
    for h in held:
        out.append(game.player.mode)
        game.tick(bool(h))
    return out


def mode_mismatches(level, held, brain: pd.DataFrame) -> int:
    modes = shown_modes(level, held)
    if len(brain) != len(modes) or (brain["tick_seen"].to_numpy() != np.arange(len(brain))).any():
        return max(1, abs(len(brain) - len(modes)))
    return int((brain["mode"].to_numpy() != np.array(modes)).sum())


def _any(brain, cols):
    present = [c for c in cols if c in brain]
    return (brain[present] > 0).any(axis=1) if present else pd.Series(False, index=brain.index)


def rule_mismatches(brain: pd.DataFrame) -> int:
    gf = _any(brain, ["spikes_GF_R", "spikes_GF_L"])
    dn = _any(brain, ["spikes_DNp22_R", "spikes_DNp22_L"])
    expected = np.where(brain["mode"] == "cube", gf, ~dn)
    return int((brain["fly_press"].astype(bool).to_numpy() != expected).sum())


def encoding_mismatches(brain: pd.DataFrame) -> int:
    cube, ship = brain["mode"] == "cube", brain["mode"] == "ship"
    has_c = brain[CUBE_FIELD].notna() if CUBE_FIELD in brain else pd.Series(False, index=brain.index)
    has_s = brain[SHIP_FIELD].notna() if SHIP_FIELD in brain else pd.Series(False, index=brain.index)
    return int((cube & (~has_c | has_s)).sum() + (ship & (~has_s | has_c)).sum())


def input_rates(spikes: dict, modes, inputs: dict[str, list[int]]) -> dict:
    """{input mode: {"shown": Hz, "not shown": Hz}}: mean rate per neuron of each mode's input
    neurons over the ticks its mode was shown, and the ticks it wasn't. `modes` is the mode per frame;
    `spikes` as `load_fly_run` gives it (flyids, frame, neuron, count)."""
    modes = np.asarray(modes)
    index = {int(f): i for i, f in enumerate(spikes["flyids"])}
    out = {}
    for mode, ids in inputs.items():
        idx = np.array(sorted(index[i] for i in ids if i in index))
        keep = np.isin(spikes["neuron"], idx) & (spikes["frame"] < len(modes))
        per_frame = np.bincount(spikes["frame"][keep], weights=spikes["count"][keep], minlength=len(modes))
        row = {}
        for label, mask in (("shown", modes == mode), ("not shown", modes != mode)):
            n = int(mask.sum())
            row[label] = float(per_frame[mask].sum() / max(1, len(idx)) / n * TICKS_PER_SECOND) if n else None
        out[mode] = row
    return out
