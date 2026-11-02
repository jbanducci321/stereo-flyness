"""The Step 2 report: the untuned fly on cube levels, next to the ideal fly (D43, D44).

Reads fly-driven runs from scripts/play_cube.py and the ideal fly from scripts/ideal_fly.py, and
writes one table: per level, how far each setting got and why it died, with the ideal 39° fly
beside it. The baseline of record comes first; the two comparisons are reported next to it and
never replace it (D43). Deaths use the D44/D45 classes: (a) invisible to the encoding, (b)
visible, but the cube still hit it, (c) short run-up.

Nothing here chooses anything: Step 2 is untuned, and the report is the same whatever it shows.

Usage (Step 2, after the held-out runs and `ideal_fly.py --suite held_out`):
    uv run python scripts/step2_report.py
    uv run python scripts/step2_report.py --suite training   # a check on training runs only

Writes results/step2/<network>_<suite>.md and .csv (git-ignored).
"""

import argparse
import json
import math
import sys
import tomllib
from types import SimpleNamespace

import pandas as pd

from analyse_pathway_tests import md_table
from ideal_fly import NO_PATCHES
from inspect_encoding import INVISIBLE, LEVELS, SHORT_RUN_UP, THRESHOLD_DEG, death_cause, job
from run_pathway_tests import ROOT
from stereo_flyness.game.player import Player
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.encoding import CubeEncoder

RUNS = ROOT / "results" / "closed_loop"
IDEAL = ROOT / "results" / "ideal_fly"
OUT = ROOT / "results" / "step2"
DIFFICULTIES = ("easy", "medium", "hard")


def settings() -> dict:
    """The Step 2 settings (D43, D45), as play_cube.py names their folders. Baseline first."""
    cfg = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())
    tf, flat = cfg["theta_full_deg"], cfg["flat_theta_full_deg"]
    return {"baseline": (f"{tf:g}deg_collision_R150", "collision"),
            "comparison 1 (pre-D45 flat R)": (f"{flat:g}deg_collision_R150_flat", "collision"),
            "comparison 2 (every object looms)": (f"{tf:g}deg_all_R150", "all")}


def death_class(cause: str | None) -> str | None:
    if cause is None:
        return None
    return "a" if cause.startswith(INVISIBLE) else "c" if cause.startswith(SHORT_RUN_UP) else "b"


def classify(folder, level, mode) -> dict:
    """One recorded fly-driven run: how far it got and, if it died, why (D44's classes, at 39°),
    plus θ at the fly's last press before dying."""
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if run.get("driver") != "fly":
        raise ValueError(f"{folder} isn't a fly-driven run")
    ticks = pd.read_parquet(folder / "ticks.parquet")
    out = {"completed": summary["completed"], "progress": summary["progress"], "jumps": summary["jumps"],
           "stuck": run.get("stuck_from_frame") is not None, "cause": None, "last_press": None}
    if summary["completed"]:
        return out
    # Rebuild what the encoding showed after each tick (same convention as ideal_fly's trace).
    enc = CubeEncoder(level, NO_PATCHES, 180.0, 150.0, mode)  # θ doesn't depend on θ_full or R
    rows = []
    for t in ticks.itertuples():
        o, theta = enc.nearest(Player(x=t.x, y=t.y, vy=t.vy, mode=t.mode, on_ground=t.on_ground))
        rows.append((t.tick, t.x, t.y, t.vy, t.on_ground, None if o is None else o.x0,
                     math.degrees(theta), t.held))
    trace = pd.DataFrame(rows, columns=["tick", "x", "y", "vy", "on_ground", "obstacle_x0", "theta", "held"])
    last = ticks.iloc[-1]
    death = SimpleNamespace(kind=summary["death_kind"], x=summary["death_x"], y=summary["death_y"], tick=int(last["tick"]))
    out["cause"] = death_cause(level, death, trace, THRESHOLD_DEG)
    pressed = trace[trace["held"].shift(-1, fill_value=False)]  # the state the press responded to
    if len(pressed):
        p = pressed.iloc[-1]
        out["last_press"] = f"θ {p['theta']:.0f}°, {int(death.tick - p['tick'])} ticks before death"
    return out


def collect(network, suite) -> pd.DataFrame:
    base = RUNS / network if suite == "training" else RUNS / network / suite
    ideal_file = IDEAL / ("all50.csv" if suite == "training" else "held_out20.csv")
    ideal = pd.read_csv(ideal_file) if ideal_file.exists() else None
    rows = []
    for name, (folder, mode) in settings().items():
        runs = base / folder / "fly"
        for level_dir in sorted(runs.glob("cube-*")) if runs.is_dir() else []:
            level, _ = load_level(LEVELS, job(level_dir.name, suite))
            r = classify(level_dir, level, mode)
            rows.append({"setting": name, "level": level_dir.name, **r, "class": death_class(r["cause"])})
    df = pd.DataFrame(rows)
    if df.empty:
        sys.exit(f"No fly-driven Step 2 runs under {base}. Run scripts/play_cube.py first.")
    if ideal is not None:
        ideal = ideal[(ideal["threshold"] == THRESHOLD_DEG) & ideal["level"].isin(df["level"])]
        for mode, label in (("collision", "ideal fly (collision course)"), ("all", "ideal fly (every object looms)")):
            for r in ideal[ideal["mode"] == mode].to_dict("records"):
                cause = r["cause"] if isinstance(r["cause"], str) else None
                rows.append({"setting": label, "level": r["level"], "completed": r["completed"],
                             "progress": r["progress"], "jumps": None, "stuck": False, "cause": cause,
                             "last_press": None, "class": death_class(cause)})
        df = pd.DataFrame(rows)
    df["difficulty"] = df["level"].str.split("-").str[1]
    return df


def report(df, network, suite) -> str:
    order = [s for s in [*settings(), "ideal fly (collision course)", "ideal fly (every object looms)"] if s in set(df["setting"])]
    lines = [f"# Step 2: the untuned fly on {suite.replace('_', '-')} cube levels (`{network}`)\n",
             "Fly-driven closed loop, no tuning (D43). The baseline of record is calibrated θ_full, collision-course "
             "looming, R × f at R = 150 Hz; the comparisons sit beside it and never replace it. The ideal fly has no "
             "brain: it presses whenever θ ≥ 39°, one tick late (D44).\n"]
    if suite != "held_out":
        lines.append("**Check only: these are training levels, not the Step 2 result.**\n")
    lines += ["## Levels completed and mean progress\n",
              "| Setting | " + " | ".join(DIFFICULTIES) + " | All | Mean progress | Deaths (a) / (b) / (c) | Stuck runs |",
              "|---|" + "---|" * (len(DIFFICULTIES) + 4)]
    for s in order:
        g = df[df["setting"] == s]
        cells = []
        for d in DIFFICULTIES:
            gd = g[g["difficulty"] == d]
            cells.append(f"{int(gd['completed'].sum())}/{len(gd)}" if len(gd) else "–")
        dead = g[~g["completed"].astype(bool)]
        classes = " / ".join(str(int((dead["class"] == c).sum())) for c in "abc")
        stuck = "–" if s.startswith("ideal") else str(int(g["stuck"].sum()))
        lines.append(f"| {s} | " + " | ".join(cells) + f" | {int(g['completed'].sum())}/{len(g)} | "
                     f"{100 * g['progress'].mean():.0f}% | {classes} | {stuck} |")
    lines += ["", "## Per level (progress; death class)\n"]
    wide = df.assign(cell=[f"{100 * p:.0f}%" + ("" if c else f" ({k})") for p, c, k in
                           zip(df["progress"], df["completed"].astype(bool), df["class"])])
    table = wide.pivot(index="level", columns="setting", values="cell")[order].reset_index()
    lines.append(md_table(table, 0))
    lines += ["", "## Deaths, with the cause\n"]
    dead = df[~df["completed"].astype(bool)].copy()
    dead["progress"] = (100 * dead["progress"]).round(0)
    dead = dead.rename(columns={"last_press": "last press (θ of what was looming then)"})
    lines.append(md_table(dead[["setting", "level", "progress", "cause", "last press (θ of what was looming then)"]]
                          .fillna("–"), 0))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="final")
    parser.add_argument("--suite", default="held_out", choices=["held_out", "training"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    df = collect(args.network, args.suite)
    text = report(df, args.network, args.suite)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{args.network}_{args.suite}.csv", index=False)
    (OUT / f"{args.network}_{args.suite}.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
