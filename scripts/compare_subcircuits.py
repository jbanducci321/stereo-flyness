"""Put several validated subcircuits side by side (J5, for the S5 decision).

Reads results/subcircuits/<name>/summary.json (written by scripts/validate_subcircuit.py) and
prints one markdown table: size, speed, and fidelity on training vs held-out conditions.

Usage:
    uv run python scripts/compare_subcircuits.py w1_1hop w2_2hop a1_active
"""

import argparse
import json
import sys

from run_pathway_tests import ROOT


def pct(v, digits=0):
    return "–" if v is None else f"{100 * v:.{digits}f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()

    rows = []
    for name in args.names:
        path = ROOT / "results" / "subcircuits" / name / "summary.json"
        if not path.exists():
            sys.exit(f"No summary for {name}. Run scripts/validate_subcircuit.py {name} first.")
        s = json.loads(path.read_text())
        h, t = s["held-out"], s["train"]
        rows.append([
            name, s["spec"].get("description", ""), f"{s['neurons']:,}", f"{s['connections'] / 1e6:.2f}M",
            f"{s['speed_up_median']:.1f}×", f"{s['x_real_time_median']:.1f}×",
            "yes" if s["verdicts_same"] else "**no**: " + ", ".join(s["verdict_mismatches"]),
            f"{pct(t['key_median_abs_rel_error'], 1)} / {pct(t['key_worst_abs_rel_error'])}",
            f"{pct(h['key_median_abs_rel_error'], 1)} / {pct(h['key_worst_abs_rel_error'])}",
            f"{h['r_median']:.3f} / {h['r_min']:.3f}",
            f"{pct(h['kept_active_median'])} / {pct(h['kept_active_min'])}",
        ])
    cols = ["candidate", "rule", "neurons", "connections", "speed-up", "× real time", "same verdicts",
            "key error, train (median / worst)", "key error, held-out (median / worst)",
            "held-out r (median / lowest)", "held-out active kept (median / lowest)"]
    sys.stdout.reconfigure(encoding="utf-8")
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
