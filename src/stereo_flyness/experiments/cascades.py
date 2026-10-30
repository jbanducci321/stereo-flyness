"""Runaway cascades in whole-brain trials (D37; docs/cascades.md).

A trial is a **cascade** if its number of active neurons is more than `ratio` times the median of
the same condition's other trials *and* more than `min_extra` above that median (`[cascade]` in
configs/pathway_tests.toml). Cascade trials are left out of subcircuit builds and out of
validation rules 2-4, and are reported separately.

The **stuck-state share** is a diagnostic, not the rule: the share of the known self-sustaining
state's neurons (configs/stuck_state_783.csv) that fire in a trial. The known cascades score
97-98%, every other trial at most ~8%.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def cascade_flags(counts: dict, ratio: float, min_extra: float) -> dict:
    """{trial: is a cascade} for one condition, from {trial: number of active neurons}."""
    flags = {}
    for t, n in counts.items():
        others = [v for k, v in counts.items() if k != t]
        med = float(np.median(others)) if others else None
        flags[t] = med is not None and n > ratio * med and n - med > min_extra
    return flags


def active_count(path) -> int:
    """How many neurons fired in a saved trial (D34 record)."""
    with np.load(path) as z:
        return len(z["all_ids"])


def find_cascades(conds, out_dir, ratio: float, min_extra: float) -> set[tuple[str, int]]:
    """(condition key, trial) of every saved cascade trial among `conds`."""
    found = set()
    for c in conds:
        counts = {t: active_count(c.path(out_dir, t)) for t in range(c.trials) if c.path(out_dir, t).exists()}
        found |= {(c.key, t) for t, flag in cascade_flags(counts, ratio, min_extra).items() if flag}
    return found


def load_stuck_state(path) -> np.ndarray:
    return pd.read_csv(path, comment="#")["flywire_id"].to_numpy(np.int64)


def save_stuck_state(path, ids, note: str) -> None:
    path = Path(path)
    path.write_text(f"# {note}\n" + pd.DataFrame({"flywire_id": sorted(int(i) for i in ids)}).to_csv(index=False),
                    encoding="utf-8")


def stuck_share(active_ids, stuck_ids) -> float:
    """Share of the stuck-state neurons among `active_ids`."""
    return float(np.isin(stuck_ids, active_ids).mean()) if len(stuck_ids) else float("nan")
