"""Whole-brain recruitment runs for the final subcircuit (D43, D36).

Each run plays one training level bot-driven (the brain only watches) under one encoding
setting. The neurons that fire in these runs join the final subcircuit's recruited set, so it
covers every setting Steps 2 and 3 will use. Settings come from configs/recruitment.toml:
- the calibrated θ_full at each R of the Step 3 tuning range (collision-course looming, R x f);
- comparison 1, the pre-D45 encoding: flat R = 150 Hz at its own calibrated θ_full (D45);
- every object looms, calibrated θ_full, R = 150 Hz (comparison 2).

A run that enters the stuck state contributes only the frames before the D38 flag starts.
"""

import json
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Setting:
    name: str
    theta_full_deg: float
    rate_hz: float
    mode: str  # "collision" or "all" (D41)
    rate_scaling: bool  # driven neurons fire at R x f (D45) or at R (the pre-D45 encoding)


def settings(cfg: dict, theta_full_deg: float, flat_theta_full_deg: float) -> list[Setting]:
    """The 7 encoding settings of D43/D45, for the calibrated θ_full of the R x f encoding and of
    the flat-rate (pre-D45) encoding."""
    for value, name in ((theta_full_deg, "theta_full"), (flat_theta_full_deg, "flat_theta_full")):
        if not value or value <= 0:
            raise ValueError(f"The calibrated {name} is needed (D43, D45): log it in configs/recruitment.toml "
                             f"or pass --{name.replace('_', '-')}.")
    s = cfg["settings"]
    out = [Setting(f"calibrated_R{r:g}", theta_full_deg, float(r), "collision", True)
           for r in s["calibrated_rates_hz"]]
    out.append(Setting(f"preD45_flat_R{s['flat_rate_hz']:g}", flat_theta_full_deg, s["flat_rate_hz"], "collision",
                       False))
    out.append(Setting(f"all_R{s['every_object_looms_rate_hz']:g}", theta_full_deg, s["every_object_looms_rate_hz"],
                       "all", True))
    return out


def run_seed(base_seed: int, level: str, setting: Setting) -> int:
    """A fixed Poisson seed per run, from its name (like the pathway tests)."""
    return zlib.crc32(f"{base_seed}/recruitment/{level}/{setting.name}".encode()) & 0x7FFFFFFF


def run_dir(out: Path, level: str, setting: Setting) -> Path:
    return Path(out) / setting.name / level


def is_done(folder: Path) -> bool:
    return (Path(folder) / "run.json").exists()


def recruited_neurons(folders) -> tuple[set[int], dict]:
    """FlyWire IDs of every neuron that fired in the given recorded runs (`fly_log` folders),
    counting only frames before each run's stuck flag. Also returns a small report."""
    ids, report = set(), {"runs": 0, "stuck_runs": 0, "frames_used": 0, "frames_dropped": 0}
    for folder in folders:
        folder = Path(folder)
        run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        if run.get("driver") != "bot":
            raise ValueError(f"{folder} isn't a bot-driven recruitment run")
        with np.load(folder / "spikes.npz") as z:
            flyids, frame, neuron = z["flyids"], z["frame"], z["neuron"]
        n_frames = int(run["ticks"])  # one brain frame per game tick (D40)
        stop = run.get("stuck_from_frame")
        keep = frame < stop if stop is not None else np.ones(len(frame), dtype=bool)
        ids |= set(int(i) for i in flyids[np.unique(neuron[keep])])
        report["runs"] += 1
        report["stuck_runs"] += stop is not None
        used = n_frames if stop is None else min(stop, n_frames)
        report["frames_used"] += used
        report["frames_dropped"] += n_frames - used
    return ids, report
