"""Step 3 runs: the open-loop check at each rate, then the tuning grid (configs/step3.toml).

`check`: the official calibration loom (start gap 245, R x f, the calibrated θ_full) at each rate,
open loop on the final subcircuit, to see where each rate makes the Giant Fiber first fire before
any game is played (proposal section 2). About 10 minutes.

`margin`: the default rate (150 Hz) at the margin seed (1) on all 50 training levels: with the
grid's seed-0 run at 150 Hz, it measures the tie margin (Shannyn, 2026-11-02). ~1.5 h.

`grid`: fly-driven closed loop at each rate on all 50 cube training levels, seed 0 (section 3).
At most ~8 h with 4 at once; fly-driven runs end when the cube dies, so usually less.

`held-out --rate R`: the chosen rate on the 20 held-out cube levels at seeds 0-2, blind
(`--quiet`, D33). Only after the grid has picked R. ~2 h.

Both call the existing scripts (calibrate_theta_full.py, play_cube.py) once per rate, so every
run is recorded and labelled exactly as theirs are. Commit before running, so each run's
recorded commit matches the code.

Usage:
    uv run python scripts/step3_grid.py check
    uv run python scripts/step3_grid.py margin
    uv run python scripts/step3_grid.py grid
    uv run python scripts/step3_grid.py held-out --rate 75
    uv run python scripts/step3_grid.py grid --dry-run     # print the commands only

Then score with scripts/step3_report.py.
"""

import argparse
import subprocess
import sys
import tomllib

from run_pathway_tests import ROOT

CONFIG = ROOT / "configs" / "step3.toml"
SCRIPTS = ROOT / "scripts"
TAG = "_step3"  # its own folders, so the D46 records at R = 150 (calibration, rule 5) aren't overwritten


def config() -> dict:
    cfg = tomllib.loads(CONFIG.read_text())
    cfg["theta_full_deg"] = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    return cfg


def levels(suite: str) -> list[str]:
    """All cube levels of a suite, as generated (held-out names carry their own seeds, e.g.
    cube-easy-1000000), checked against the counts in configs/level_suites.toml."""
    names = sorted(p.stem for p in (ROOT / "results" / "levels" / suite).glob("cube-*.json") if not p.stem.endswith(".meta"))
    counts = tomllib.loads((ROOT / "configs" / "level_suites.toml").read_text())["suites"][suite]["cube"]
    if len(names) != sum(counts.values()):
        sys.exit(f"Expected {sum(counts.values())} cube levels in results/levels/{suite}, found {len(names)}.")
    return names


def play(cfg, suite, rate, seed, jobs, quiet=False) -> list[str]:
    return [sys.executable, "-u", str(SCRIPTS / "play_cube.py"), *levels(suite), "--suite", suite,
            "--network", cfg["network"], "--theta-full", f"{cfg['theta_full_deg']:g}", "--rate", f"{rate:g}",
            "--rate-scaling", "--seed", str(seed), "--tag", TAG, "--jobs", str(jobs), *(["--quiet"] if quiet else [])]


def commands(what: str, cfg: dict, jobs: int, rate: float | None = None) -> list[list[str]]:
    if what == "check":
        return [[sys.executable, "-u", str(SCRIPTS / "calibrate_theta_full.py"), "--network", cfg["network"],
                 "--rate-scaling", "--rate", f"{r:g}", "--grid", f"{cfg['theta_full_deg']:g}", "--trials",
                 str(cfg["check_trials"]), "--start-gap", f"{cfg['check_start_gap']:g}", "--tag", TAG,
                 "--jobs", str(jobs)] for r in cfg["rates_hz"]]
    if what == "margin":
        return [play(cfg, cfg["suite"], cfg["default_rate_hz"], cfg["margin_seed"], jobs)]
    if what == "held-out":
        if rate not in cfg["rates_hz"] or rate == cfg["default_rate_hz"]:
            sys.exit("--rate must be the grid's pick, and not the default (then the held-out run isn't repeated)")
        return [play(cfg, "held_out", rate, seed, jobs, quiet=True) for seed in cfg["held_out_seeds"]]
    return [play(cfg, cfg["suite"], r, cfg["seed"], jobs) for r in cfg["rates_hz"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["check", "margin", "grid", "held-out"])
    parser.add_argument("--rate", type=float, help="held-out only: the rate the grid picked")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    for cmd in commands(args.what, config(), args.jobs, args.rate):
        print(" ".join(c if " " not in c else f'"{c}"' for c in cmd[2:]) if args.dry_run or args.what != "held-out"
              else f"held-out run at seed {cmd[cmd.index('--seed') + 1]}", flush=True)
        if not args.dry_run:
            subprocess.run(cmd, cwd=SCRIPTS, check=True)


if __name__ == "__main__":
    main()
