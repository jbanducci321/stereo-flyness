"""Step 4's judging rules (D51), fixed before any run. Used by scripts/step4_report.py.

- `paired`: per level, each setting's median run across its 3 seeds or instances, D48's "equal",
  then the two-sided sign test (equal levels left out).
- `holm`: Holm's step-down correction over the family D51 names (10 sign tests).
- `relay_reading`: Shannyn's three relay bars for controls (b) and (c): progress shows no clear
  difference, and the pooled median first-spike θ (without carry-over) and the (d1) share of deaths
  each differ from the intact brain's by no more than the largest difference between two intact seeds.
- `specific`: a lesion's effect is specific if it differs from intact and from its own random-lesion
  control at p < 0.05, in the same direction.
"""

from dataclasses import dataclass
from itertools import combinations
from statistics import median

from stereo_flyness.experiments.step2_analysis import compare, sign_test

ALPHA = 0.05


@dataclass
class Paired:
    better: int
    worse: int
    equal: int
    p: float

    @property
    def reading(self) -> str:
        if self.p < ALPHA:
            return "better" if self.better > self.worse else "worse"
        return "no clear difference"


def median_runs(runs: list[dict]) -> dict:
    """Per level, the run with the median progress across seeds (ties broken by the lower seed).

    An actual run, so it has a killing object. `runs` are dicts with level, seed and progress.
    """
    by_level: dict[str, list[dict]] = {}
    for r in runs:
        by_level.setdefault(r["level"], []).append(r)
    out = {}
    for level, rs in by_level.items():
        rs = sorted(rs, key=lambda r: (r["progress"], r["seed"]))
        out[level] = rs[(len(rs) - 1) // 2]
    return out


def paired(condition: list[dict], reference: list[dict]) -> Paired:
    """The condition against the reference, level by level on their median runs (D48, D51)."""
    c, r = median_runs(condition), median_runs(reference)
    if set(c) != set(r):
        raise ValueError("the condition and the reference cover different levels")
    signs = [compare(c[lv], r[lv]) for lv in sorted(c)]
    better, worse = signs.count(1), signs.count(-1)
    return Paired(better, worse, signs.count(0), sign_test(better, worse))


def holm(pvalues: dict[str, float], alpha: float = ALPHA) -> dict[str, tuple[float, bool]]:
    """Holm's step-down correction: name -> (adjusted p, rejected at alpha)."""
    order = sorted(pvalues, key=lambda k: pvalues[k])
    m, running, out, stop = len(order), 0.0, {}, False
    for i, name in enumerate(order):
        adj = min(1.0, (m - i) * pvalues[name])
        running = max(running, adj)  # adjusted p-values never decrease down the order
        stop = stop or running >= alpha
        out[name] = (running, not stop)
    return out


def seed_range(values: list[float]) -> float:
    """The largest difference between any two values (the intact brain's seed-to-seed range)."""
    return max((abs(a - b) for a, b in combinations(values, 2)), default=0.0)


def d1_share(classes: list[str | None]) -> float:
    """Share of deaths that are (d1); completed runs (class None) aren't deaths. No deaths -> 0 (D51)."""
    deaths = [c for c in classes if c is not None]
    return sum(c == "d1" for c in deaths) / len(deaths) if deaths else 0.0


def pooled_median(thetas: list[float]) -> float | None:
    """Median first-spike θ over pooled approaches; None if the Giant Fiber never fired (D51: fails)."""
    return median(thetas) if thetas else None


@dataclass
class RelayReading:
    progress_ok: bool
    theta_ok: bool
    d1_ok: bool
    theta_diff: float | None
    theta_range: float
    d1_diff: float
    d1_range: float

    @property
    def verdict(self) -> str:
        if not self.progress_ok:
            return "plays differently from intact"
        if self.theta_ok and self.d1_ok:
            return "relay: all three bars pass"
        return "plays about as far, but not the same way"


def relay_reading(progress: Paired, cond_theta: list[float], intact_theta_by_seed: list[list[float]],
                  cond_classes: list, intact_classes_by_seed: list[list]) -> RelayReading:
    """Shannyn's three relay bars (D51) for one control against the intact brain."""
    intact_theta = pooled_median([t for s in intact_theta_by_seed for t in s])
    theta_range = seed_range([pooled_median(s) for s in intact_theta_by_seed if s])
    c_theta = pooled_median(cond_theta)
    theta_diff = None if c_theta is None or intact_theta is None else abs(c_theta - intact_theta)
    d1_range = seed_range([d1_share(s) for s in intact_classes_by_seed])
    d1_diff = abs(d1_share(cond_classes) - d1_share([c for s in intact_classes_by_seed for c in s]))
    return RelayReading(progress.reading == "no clear difference",
                        theta_diff is not None and theta_diff <= theta_range,
                        d1_diff <= d1_range, theta_diff, theta_range, d1_diff, d1_range)


def specific(lesion_vs_intact: Paired, lesion_vs_random: Paired) -> bool:
    """D51: the lesion differs from intact and from its own random-lesion control, same direction."""
    a, b = lesion_vs_intact.reading, lesion_vs_random.reading
    return a != "no clear difference" and a == b
