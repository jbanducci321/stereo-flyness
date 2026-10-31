"""Recording closed-loop runs (R1, D19, D38): what the game did, what we fed the brain, what it did.

A run is saved as a folder:
    ticks.parquet, summary.json   the game's standard run log (`game.recorder.RunLog`), so the
                                  replay viewer plays fly runs exactly like bot runs
    brain.parquet                 one row per brain frame: our input (θ, f, driven counts, R) kept
                                  apart from the fly's activity (watched spike counts, active
                                  neurons, the stuck-state share and flags; hard rule 10)
    spikes.npz                    every neuron that fired, per frame, stored sparsely (as D34)
    run.json                      who drove the cube ("fly" or "bot"), settings, flags, commit

Frame i saw the game after i ticks, and its press is the `held` of game tick i + 1 (D40).

Flags (D38):
- **stuck state:** at least `stuck_share` of the stuck-state neurons (the whole-brain list,
  restricted to the network that's running) fired within the last `window` frames (~100 ms).
  Computed live, frame by frame. A run is flagged from the first frame it's true.
- **backup:** the number of distinct neurons active within the window, **not counting the
  neurons we stimulate** (`stimulated_ids`), is above `backup_factor` times the run's own
  median, and above `backup_floor` (1,000; D38 amendment). Computed when the run ends, since it
  needs the median. The floor is needed because a quiet run's median can be near 0, and 3 x 0
  would flag any activity at all. Leaving out the stimulated neurons keeps our input from
  counting as the fly's activity (hard rule 10), e.g. thousands of T4/T5 in ship mode.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from stereo_flyness.game.recorder import RunLog

WINDOW_TICKS = 24  # ~100 ms at 240 Hz


class _Window:
    """Neurons that fired at least once in the last `size` frames, kept incrementally."""

    def __init__(self, n, size):
        self.count, self.size, self.recent, self.distinct = np.zeros(n, dtype=np.int32), size, [], 0

    def push(self, active):
        self.distinct += int((self.count[active] == 0).sum())
        self.count[active] += 1
        self.recent.append(active)
        if len(self.recent) > self.size:
            old = self.recent.pop(0)
            self.count[old] -= 1
            self.distinct -= int((self.count[old] == 0).sum())


class FlyRecorder:
    def __init__(self, game, flyids, driver: str, stuck_ids=(), meta: dict | None = None,
                 stimulated_ids=(), window: int = WINDOW_TICKS, stuck_share: float = 0.5, backup_factor: float = 3.0,
                 backup_floor: int = 1000):
        if driver not in ("fly", "bot"):
            raise ValueError("driver must be 'fly' or 'bot'")
        self.driver, self.meta = driver, dict(meta or {})
        self.flyids = np.asarray(flyids, dtype=np.int64)
        index = {int(f): i for i, f in enumerate(self.flyids)}
        self.stuck_idx = np.array(sorted(index[int(i)] for i in stuck_ids if int(i) in index), dtype=np.int64)
        self.stim_idx = np.array(sorted({index[int(i)] for i in stimulated_ids if int(i) in index}), dtype=np.int64)
        self.settings = {"window_frames": window, "stuck_share": stuck_share, "backup_factor": backup_factor,
                         "backup_floor": backup_floor, "stuck_neurons": int(len(self.stuck_idx)),
                         "stimulated_neurons_excluded": int(len(self.stim_idx))}
        self.game_log = RunLog(game.level.name)
        self.rows, self._frames, self._neurons, self._counts = [], [], [], []
        self._all = _Window(len(self.flyids), window)
        self._stuck = _Window(len(self.flyids), window)
        self.stuck_from = None

    def frame(self, game, held: bool, brain_row: dict, last_counts) -> None:
        """Record frame i: call right after `game.tick(held)` with frame i's activity."""
        i = len(self.rows)
        active = np.flatnonzero(last_counts)
        self._frames.append(np.full(len(active), i, dtype=np.int32))
        self._neurons.append(active.astype(np.int32))
        self._counts.append(np.asarray(last_counts)[active].astype(np.uint16))
        self._all.push(np.setdiff1d(active, self.stim_idx, assume_unique=True))
        self._stuck.push(np.intersect1d(active, self.stuck_idx, assume_unique=True))
        share = self._stuck.distinct / len(self.stuck_idx) if len(self.stuck_idx) else 0.0
        stuck = share >= self.settings["stuck_share"]
        if stuck and self.stuck_from is None:
            self.stuck_from = i
        self.game_log.append(game, held)
        self.rows.append({"frame": i, **brain_row, "held": held, "active_neurons": int(len(active)),
                          "active_in_window": self._all.distinct, "stuck_share": share, "stuck_flag": stuck})

    def finish(self, game, extra: dict | None = None) -> dict:
        self.game_log.finish(game)
        brain = pd.DataFrame(self.rows)
        window = brain["active_in_window"] if len(brain) else pd.Series(dtype=float)
        median = float(window.median()) if len(window) else 0.0
        limit = max(self.settings["backup_factor"] * median, self.settings["backup_floor"])
        flagged = np.flatnonzero(window.to_numpy() > limit) if len(window) else np.array([])
        self.backup = {"median_active_in_window": median, "limit": limit,
                       "from_frame": int(flagged[0]) if len(flagged) else None, "frames": int(len(flagged))}
        if len(brain):
            brain["backup_flag"] = window > limit
        self.brain = brain
        self.summary = {"driver": self.driver, **self.game_log.summary.__dict__,
                        "stuck_from_frame": self.stuck_from, "backup_from_frame": self.backup["from_frame"],
                        "flags": {**self.settings, "backup": self.backup}, **self.meta, **(extra or {})}
        return self.summary

    def save(self, folder) -> Path:
        folder = Path(folder)
        self.game_log.save(folder)
        self.brain.to_parquet(folder / "brain.parquet", index=False)
        cat = lambda xs, dt: np.concatenate(xs) if xs else np.zeros(0, dtype=dt)  # noqa: E731
        np.savez_compressed(folder / "spikes.npz", flyids=self.flyids, frame=cat(self._frames, np.int32),
                            neuron=cat(self._neurons, np.int32), count=cat(self._counts, np.uint16))
        (folder / "run.json").write_text(json.dumps(self.summary, indent=1, default=str), encoding="utf-8")
        return folder


def load_fly_run(folder) -> dict:
    """A saved run: the game log, the brain table, the sparse spikes and run.json."""
    folder = Path(folder)
    with np.load(folder / "spikes.npz") as z:
        spikes = {k: z[k] for k in z.files}
    return {"game": RunLog.load(folder), "brain": pd.read_parquet(folder / "brain.parquet"), "spikes": spikes,
            "run": json.loads((folder / "run.json").read_text(encoding="utf-8"))}
