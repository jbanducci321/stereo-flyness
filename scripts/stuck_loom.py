"""Can a stuck brain still jump? A loom during the stuck state (follow-up (a), docs/cascades.md).

Reproducing a cascade by its seed doesn't work once input groups are added (the Poisson draws
change), so the stuck state is switched on deliberately instead:
    0-200 ms      "ignite": the stuck-state neurons (configs/stuck_state_783.csv) at 50 Hz,
                  leaving out the looming neurons and the Giant Fibers
    200-700 ms    no input: the state must keep itself going (checked: stuck-state share
                  from 300 ms on, and neurons active per frame)
    700-1000 ms   a loom: all right LC4 + LPLC2 at 150 Hz
    1000-1200 ms  no input
Control: the same groups and schedule with the ignite input at 0 Hz, so only the stuck state
differs. Each pair shares seeds (same condition name), whole brain, original signs.

Usage:
    uv run python scripts/stuck_loom.py --trials 5 --jobs 4
    uv run python scripts/stuck_loom.py --ignite-hz 10 --ignite-ms 100 --trials 2

A strong ignite (50 Hz, 200 ms) gives a larger state than the natural one (~12,500 neurons, ~5,800
active per frame, against ~8,300 and ~2,000); weaker ignites may land in the natural state.
"""

import argparse
import sys
import tomllib

import numpy as np
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from run_pathway_tests import CON_PATHS, CONFIG, OUT, PATH_COMP, ROOT, git_commit
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.cascades import load_stuck_state, stuck_share
from stereo_flyness.experiments.pathway_tests import Condition, load_trial, n_frames, run_trial

RESULTS = OUT.parent / "cascades" / "stuck_loom"
IGNITE_HZ, LOOM_HZ = 50, 150
PHASES_MS = {"ignite": 200, "settle": 500, "loom": 300, "after": 200}


def conds(cells, stuck, fr, trials, ignite_hz, ignite_ms):
    loom = {"loom_LC4_R": cells.ids("LC4", side="right"), "loom_LPLC2_R": cells.ids("LPLC2", side="right")}
    keep_out = {i for v in loom.values() for i in v} | set(cells.ids("DNp01"))
    ignite = sorted(int(i) for i in stuck if int(i) not in keep_out)
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    out = []
    for kind, hz in (("stuck", ignite_hz), ("control", 0)):
        schedule = [(n_frames(ignite_ms, fr), {"ignite": hz}),
                    (n_frames(PHASES_MS["settle"] + PHASES_MS["ignite"] - ignite_ms, fr), {}),
                    (n_frames(PHASES_MS["loom"], fr), {g: LOOM_HZ for g in loom}),
                    (n_frames(PHASES_MS["after"], fr), {})]
        # Same name for both, so trial t gets the same seed in each; they're saved apart
        out.append((kind, Condition("X1", "X1/stuck_then_loom_R", "original", {"ignite": ignite, **loom},
                                    schedule, gf, [], trials, "right")))
    return out, len(ignite)


def window(tr, a_ms, b_ms):
    fr = tr["meta"]["frame_ms"]
    return slice(int(round(a_ms / fr)), int(round(b_ms / fr)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--ignite-hz", type=float, default=IGNITE_HZ)
    parser.add_argument("--ignite-ms", type=float, default=PHASES_MS["ignite"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    stuck = load_stuck_state(ROOT / cfg["cascade"]["stuck_state"])
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    pairs, n_ignite = conds(cells, stuck, cfg["frame_ms"], args.trials, args.ignite_hz, args.ignite_ms)
    out = RESULTS / f"ignite_{args.ignite_hz:g}Hz_{args.ignite_ms:g}ms"
    meta = {"commit": git_commit(), "purpose": "loom during the stuck state (stuck_loom.py)"}
    Parallel(n_jobs=args.jobs)(
        delayed(run_trial)(c, t, out / kind, PATH_COMP, CON_PATHS["original"], cfg["base_seed"],
                           cfg["frame_ms"], meta) for kind, c in pairs for t in range(args.trials))

    settle_end = PHASES_MS["ignite"] + PHASES_MS["settle"]
    loom_end = settle_end + PHASES_MS["loom"]
    rows = []
    for kind, c in pairs:
        for t in range(args.trials):
            tr = load_trial(c.path(out / kind, t))
            fr = tr["meta"]["frame_ms"]
            late = window(tr, PHASES_MS["ignite"] + 100, settle_end)  # input off for >= 100 ms
            on = tr["all_spikes"][late].any(axis=0)
            per_frame = (tr["all_spikes"][late] > 0).sum(axis=1).mean()
            row = {"run": kind, "trial": t, "share": stuck_share(tr["all_ids"][on], stuck), "per_frame": per_frame,
                   "distinct": int(on.sum())}
            for g in ("GF_R", "GF_L"):
                s = tr["spikes"][g][:, 0]
                lw = window(tr, settle_end, loom_end)
                hit = np.flatnonzero(s[lw])
                row[g] = s[lw].sum() / (PHASES_MS["loom"] / 1000)
                row[f"{g}_first"] = hit[0] * fr if len(hit) else None
                row[f"{g}_before"] = s[late].sum()
            rows.append(row)

    fmt = lambda v: "none" if v is None else f"{v:.1f}"  # noqa: E731
    lines = ["# Loom during the stuck state\n",
             f"Ignite: {n_ignite:,} stuck-state neurons at {args.ignite_hz:g} Hz for {args.ignite_ms:g} ms (0 Hz in the "
             f"control), then {PHASES_MS['settle']} ms of no input, then right LC4 + LPLC2 at {LOOM_HZ} Hz for "
             f"{PHASES_MS['loom']} ms. Whole brain, original signs; trial t uses the same seed in both runs.\n",
             "| run | trial | stuck-state share, no input | neurons active, no input | per frame | GF_R spikes before loom | "
             "GF_R Hz in loom | GF_R first spike (ms) | GF_L Hz in loom | GF_L first spike (ms) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['run']} | {r['trial']} | {r['share']:.0%} | {r['distinct']:,} | {r['per_frame']:,.0f} | {r['GF_R_before']} | "
              f"{r['GF_R']:.0f} | {fmt(r['GF_R_first'])} | {r['GF_L']:.0f} | {fmt(r['GF_L_first'])} |" for r in rows]
    for kind in ("stuck", "control"):
        rs = [r for r in rows if r["run"] == kind]
        lines.append(f"\n- **{kind}:** stuck-state share {np.mean([r['share'] for r in rs]):.0%}; GF_R "
                     f"{np.mean([r['GF_R'] for r in rs]):.0f} ± {np.std([r['GF_R'] for r in rs]):.0f} Hz, GF_L "
                     f"{np.mean([r['GF_L'] for r in rs]):.0f} ± {np.std([r['GF_L'] for r in rs]):.0f} Hz during the loom")
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
