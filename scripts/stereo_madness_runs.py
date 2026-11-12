"""Stereo Madness, the held-out final test (Step 6): every variant in configs/stereo_madness.toml at
every seed, whole brain, blind (D33), through scripts/play_level.py --stereo-madness-final.

Refuses to start unless:
- configs/stereo_madness.toml names a logged decision (`decision`, e.g. "D54") whose entry in
  docs/decisions.md mentions Stereo Madness: the settings are fixed before any run (D7);
- the tree is clean (every run records its commit);
- the ship open-loop gate passed on each connectome a variant uses (`ship_open_loop.py`);
- the mixed-level check's switching checks passed (`mixed_check_report.py`).

Runs `--parallel` games at once (one brain each), each with `--resume`: after a crash or restart,
the same command plays only what's missing at this commit. Only progress and stuck flags are
printed. Nothing is changed between or after runs.

Usage:
    uv run python scripts/stereo_madness_runs.py --dry-run
    uv run python scripts/stereo_madness_runs.py                 # every variant, in the config's order
"""

import argparse
import re
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ship_baseline_runs import GATES, gate_passed

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stereo_madness.toml"
DECISIONS = ROOT / "docs" / "decisions.md"
MIXED = ROOT / "results" / "mixed_check" / "held_out" / "report.md"


def load_config(path=CONFIG) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def decision_logged(cfg: dict, decisions_text: str) -> bool:
    d = cfg.get("decision", "").strip()
    if not re.fullmatch(r"D\d+", d):
        return False
    return any(line.startswith(f"**{d}. ") and "Stereo Madness" in line for line in decisions_text.splitlines())


def mixed_check_passed(path=MIXED) -> bool:
    return path.exists() and re.search(r"\*\*Switching\*\*.*\*\*PASS\*\*", path.read_text(encoding="utf-8")) is not None


def command(cfg: dict, variant: str, seed: int) -> list[str]:
    v = cfg["variants"][variant]
    return ["uv", "run", "python", "-u", "scripts/play_level.py", "stereo_madness", "--stereo-madness-final",
            "--network", cfg["network"], "--rate", f"{v['rate_hz']:g}", "--ship", cfg["ship_design"],
            "--ship-rate", f"{cfg['ship_rate_hz']:g}", "--signs", v["signs"], "--seed", str(seed),
            "--jobs", "1", "--quiet", "--resume"]


def refusal(cfg: dict) -> str | None:
    if not decision_logged(cfg, DECISIONS.read_text(encoding="utf-8")):
        return ("configs/stereo_madness.toml doesn't name a logged Step 6 decision. Log it in docs/decisions.md "
                "and set `decision` first (D7: settings fixed before any run).")
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        return "the tree has uncommitted changes, so every run would be -dirty. Commit first."
    for signs in sorted({v["signs"] for v in cfg["variants"].values()}):
        if not gate_passed(GATES[signs]):
            return f"the ship open-loop gate ({signs} signs) hasn't passed."
    if not mixed_check_passed():
        return "the mixed-level check's switching checks haven't passed (scripts/mixed_check_report.py)."
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parallel", type=int, default=4, help="games at once (one brain each)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    jobs = [(v, s) for v in cfg["variants"] for s in cfg["seeds"]]
    if args.dry_run:
        for v, s in jobs[:3]:
            print(" ".join(command(cfg, v, s)))
        print(f"... {len(jobs)} runs: {', '.join(cfg['variants'])} × seeds {cfg['seeds'][0]}-{cfg['seeds'][-1]}")
        why = refusal(cfg)
        print("Would refuse: " + why if why else "All gates pass.")
        return
    why = refusal(cfg)
    if why:
        sys.exit(f"Refused, nothing run: {why}")

    def run(job):
        v, s = job
        p = subprocess.run(command(cfg, v, s), cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        stuck = "; STUCK" if "STUCK" in p.stdout else ""
        print(f"{v} seed {s}: {'done' if p.returncode == 0 else 'FAILED (rerun to resume)'}{stuck}", flush=True)
        return p.returncode

    print(f"Stereo Madness ({cfg['decision']}): {len(jobs)} runs, {args.parallel} at once. Blind: outcomes not shown.",
          flush=True)
    with ThreadPoolExecutor(args.parallel) as pool:
        codes = list(pool.map(run, jobs))
    failed = sum(1 for c in codes if c)
    if failed:
        sys.exit(f"{failed} run(s) failed. Run the same command again: it plays only what's missing.")
    print(f"All {len(jobs)} runs done (outcomes not shown: blind).")


if __name__ == "__main__":
    main()
