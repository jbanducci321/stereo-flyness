"""Step 3 runs: the open-loop check at each rate, then the tuning grid (configs/step3.toml).

`check`: the official calibration loom (start gap 245, R x f, the calibrated θ_full) at each rate,
open loop on the final subcircuit, to see where each rate makes the Giant Fiber first fire before
any game is played (proposal section 2). About 10 minutes.

`grid`: fly-driven closed loop at each rate on all 50 cube training levels, seed 0 (section 3).
At most ~8 h with 4 at once; fly-driven runs end when the cube dies, so usually less.

Both call the existing scripts (calibrate_theta_full.py, play_cube.py) once per rate, so every
run is recorded and labelled exactly as theirs are. Commit before running, so each run's
recorded commit matches the code.

Usage:
    uv run python scripts/step3_grid.py check
    uv run python scripts/step3_grid.py grid
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
    """All cube levels of a suite, by the counts in configs/level_suites.toml."""
    counts = tomllib.loads((ROOT / "configs" / "level_suites.toml").read_text())["suites"][suite]["cube"]
    return [f"cube-{d}-{i}" for d, n in counts.items() for i in range(n)]


def commands(what: str, cfg: dict, jobs: int) -> list[list[str]]:
    py = [sys.executable, "-u"]
    out = []
    for rate in cfg["rates_hz"]:
        if what == "check":
            out.append([*py, str(SCRIPTS / "calibrate_theta_full.py"), "--network", cfg["network"], "--rate-scaling",
                        "--rate", f"{rate:g}", "--grid", f"{cfg['theta_full_deg']:g}", "--trials",
                        str(cfg["check_trials"]), "--start-gap", f"{cfg['check_start_gap']:g}", "--tag", TAG,
                        "--jobs", str(jobs)])
        else:
            out.append([*py, str(SCRIPTS / "play_cube.py"), *levels(cfg["suite"]), "--suite", cfg["suite"],
                        "--network", cfg["network"], "--theta-full", f"{cfg['theta_full_deg']:g}", "--rate", f"{rate:g}",
                        "--rate-scaling", "--seed", str(cfg["seed"]), "--tag", TAG, "--jobs", str(jobs)])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["check", "grid"])
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    for cmd in commands(args.what, config(), args.jobs):
        print(" ".join(c if " " not in c else f'"{c}"' for c in cmd[2:]), flush=True)
        if not args.dry_run:
            subprocess.run(cmd, cwd=SCRIPTS, check=True)


if __name__ == "__main__":
    main()
