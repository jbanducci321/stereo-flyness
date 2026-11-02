"""D36 rule 5 on a subcircuit, as amended by D46: same presses as the whole brain, per approach.

Both networks watch the same bot-driven levels with the same seed (scripts/play_cube.py --bot).
For each obstacle approach, the first press on each network is compared: matched within ±1
frame, a miss if only one presses or they're further apart. Pass at >= 95% of the approaches
in which at least one network presses. Fly-driven runs, if present, are described, not judged.

Run the levels on both networks first, for example:
    uv run python scripts/play_cube.py cube-easy-4 cube-easy-5 cube-medium-4 cube-medium-5 cube-hard-2 \\
        --network whole_brain --theta-full 200 --rate 150 --rate-scaling --bot --jobs 4
    (the same with --network final), then:
    uv run python scripts/validate_closed_loop.py final

Writes results/closed_loop/<subcircuit>/rule5.md (git-ignored).
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd

from run_pathway_tests import ROOT
from stereo_flyness.experiments.subcircuit_validation import press_agreement

OUT = ROOT / "results" / "closed_loop"
MIN_SHARE = 0.95  # D36 rule 5
LEVELS = ["cube-easy-4", "cube-easy-5", "cube-medium-4", "cube-medium-5", "cube-hard-2"]  # D43


def brain(folder):
    return pd.read_parquet(folder / "brain.parquet")


def judged(sub: str) -> tuple[list[str], dict]:
    lines = ["## Rule 5: bot-driven, first press per approach\n",
             "| Setting | Levels | Approaches | Neither pressed | Judged | Matched (±1 frame) | Only whole brain | "
             "Only subcircuit | Further apart | Frame diffs (sub − whole) | Share | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    verdicts = {}
    for setting in sorted(p.name for p in (OUT / sub).iterdir() if (p / "bot").is_dir()):
        total = {"approaches": 0, "neither": 0, "matched": 0, "only_whole": 0, "only_sub": 0, "apart": 0, "diffs": []}
        done = []
        for level in LEVELS:
            w, s = OUT / "whole_brain" / setting / "bot" / level, OUT / sub / setting / "bot" / level
            if not ((w / "brain.parquet").exists() and (s / "brain.parquet").exists()):
                continue
            r = press_agreement(brain(w), brain(s))
            for k in total:
                total[k] += r[k]
            done.append(level)
        if not done:
            continue
        n = total["approaches"] - total["neither"]
        share = total["matched"] / n if n else float("nan")
        verdict = "incomplete" if len(done) < len(LEVELS) else ("PASS" if share >= MIN_SHARE else "FAIL")
        verdicts[setting] = verdict
        d = total["diffs"]
        diffs = "–" if not d else f"{min(d):+d} to {max(d):+d} ({np.mean(np.abs(d) == 0):.0%} same frame)"
        lines.append(f"| {setting} | {len(done)}/{len(LEVELS)} | {total['approaches']} | {total['neither']} | {n} | "
                     f"{total['matched']} | {total['only_whole']} | {total['only_sub']} | {total['apart']} | {diffs} | "
                     f"{share:.1%} | **{verdict}** |")
    return lines, verdicts


def described(sub: str) -> list[str]:
    """Fly-driven runs, described only (D46): how each network's own game went."""
    rows = []
    for setting in sorted(p.name for p in (OUT / sub).iterdir() if (p / "fly").is_dir()):
        for level in LEVELS:
            w, s = OUT / "whole_brain" / setting / "fly" / level, OUT / sub / setting / "fly" / level
            if not ((w / "run.json").exists() and (s / "run.json").exists()):
                continue
            rw, rs = (json.loads((f / "summary.json").read_text(encoding="utf-8")) for f in (w, s))
            pw, ps = brain(w)["fly_press"].to_numpy(bool), brain(s)["fly_press"].to_numpy(bool)
            n = min(len(pw), len(ps))
            split = np.flatnonzero(pw[:n] != ps[:n])
            end = lambda r: "completed" if r["completed"] else f"died at {100 * r['progress']:.0f}%"  # noqa: E731
            rows.append(f"| {setting} | {level} | {end(rw)}, {rw['jumps']} jumps | {end(rs)}, {rs['jumps']} jumps | "
                        f"{'never' if not len(split) else split[0]} |")
    if not rows:
        return []
    return ["\n## Fly-driven closed loop (described, not judged)\n",
            "| Setting | Level | Whole brain | Subcircuit | First frame the presses differ |", "|---|---|---|---|---|",
            *rows]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subcircuit")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # ± and −; Windows consoles default to cp1252

    lines, verdicts = judged(args.subcircuit)
    if not verdicts:
        sys.exit(f"No paired bot-driven runs for {args.subcircuit}. Run scripts/play_cube.py --bot on both networks first.")
    text = "\n".join([f"# Closed-loop check (D36 rule 5, D46): `{args.subcircuit}` vs the whole brain\n",
                      f"Levels: {', '.join(LEVELS)}. Pass at >= {MIN_SHARE:.0%} of the approaches in which "
                      "at least one network presses. Fixed in advance (D46): a failing R is dropped from the "
                      "Step 3 range; a failing comparison runs on the whole brain.\n", *lines, *described(args.subcircuit)])
    print(text)
    out = OUT / args.subcircuit / "rule5.md"
    out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
