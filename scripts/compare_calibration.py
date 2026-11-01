"""Does a subcircuit reproduce the whole brain's θ_full calibration? (D43, D36 rule 3)

Pairs each calibration trial (same θ_full, trial and seed) on the whole brain and on the
subcircuit, and compares the frame of the Giant Fiber's first spike (right or left). The bar
(D43): within one frame (4.2 ms, about ±1.1° near 39°) in >= 95% of trials.

Run the subcircuit's calibration first, with the same grid and trials as the official one:
    uv run python scripts/calibrate_theta_full.py --network final --rate-scaling --trials 10 \\
        --grid 90 135 180 270 360 540
    uv run python scripts/compare_calibration.py final gap245_R150_scaled gap245_R150

Prints a markdown table per run folder and writes it to
results/calibration/<subcircuit>/reproduces_whole_brain.md (git-ignored).
"""

import argparse
import sys

import pandas as pd

from run_pathway_tests import ROOT

OUT = ROOT / "results" / "calibration"
MIN_SHARE = 0.95  # D36 rule 3


def first_spike(folder):
    """(frame, θ) of the first Giant Fiber spike in a recorded trial, or (None, None)."""
    b = pd.read_parquet(folder / "brain.parquet")
    hit = b.loc[(b["spikes_GF_R"] + b["spikes_GF_L"]) > 0]
    return (None, None) if hit.empty else (int(hit["frame"].iloc[0]), float(hit["theta_deg"].iloc[0]))


def compare(sub, run):
    rows = []
    for whole in sorted((OUT / "whole_brain" / run).glob("*deg/trial_*")):
        mine = OUT / sub / run / whole.parent.name / whole.name
        if not (mine / "brain.parquet").exists():
            continue
        (fw, tw), (fs, ts) = first_spike(whole), first_spike(mine)
        rows.append({"theta_full": float(whole.parent.name.removesuffix("deg")), "trial": whole.name,
                     "frame_whole": fw, "frame_sub": fs, "theta_whole": tw, "theta_sub": ts,
                     "diff": None if fw is None or fs is None else fs - fw})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subcircuit")
    parser.add_argument("runs", nargs="+", help="run folders under results/calibration/whole_brain/")
    args = parser.parse_args()

    lines = [f"# Calibration reproduced on `{args.subcircuit}`?\n",
             f"Same θ_full, trial and seed on both networks. Bar: first Giant Fiber spike within one frame "
             f"in >= {MIN_SHARE:.0%} of trials (D43, D36 rule 3).\n"]
    for run in args.runs:
        d = compare(args.subcircuit, run)
        if d.empty:
            sys.exit(f"No paired trials for {run}. Run scripts/calibrate_theta_full.py --network {args.subcircuit} first.")
        # A trial matches if both fire within one frame of each other, or neither fires.
        both_none = d["frame_whole"].isna() & d["frame_sub"].isna()
        ok = both_none | (d["diff"].abs() <= 1)
        lines += [f"## {run}\n", "| θ_full (°) | trials | within 1 frame | frame diff (sub − whole), range | "
                  "first-spike θ whole → sub, mean (°) |", "|---|---|---|---|---|"]
        for tf, g in d.groupby("theta_full"):
            rng = "–" if g["diff"].isna().all() else f"{g['diff'].min():+.0f} to {g['diff'].max():+.0f}"
            lines.append(f"| {tf:g} | {len(g)} | {int(ok[g.index].sum())}/{len(g)} | {rng} | "
                         f"{g['theta_whole'].mean():.1f} → {g['theta_sub'].mean():.1f} |")
        share = ok.mean()
        lines.append(f"\n**{int(ok.sum())}/{len(d)} trials within one frame ({share:.0%}): "
                     f"{'PASS' if share >= MIN_SHARE else 'FAIL'}.**\n")
    text = "\n".join(lines)
    sys.stdout.reconfigure(encoding="utf-8")  # θ and ±; Windows consoles default to cp1252
    print(text)
    out = OUT / args.subcircuit / "reproduces_whole_brain.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
