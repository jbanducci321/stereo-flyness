"""Record the fingerprint of every iteration-1 level, for tests/test_generator_freeze.py.

Iteration 1's suites (configs/level_suites.toml, generator v3) must rebuild exactly as they were
when the fly played them. This script reads the levels cached in results/levels/ (the ones the runs
actually used), checks that the generator rebuilds each one identically, and writes one SHA-256
per level, with the attempt the bot accepted, to tests/data/v3_level_hashes.json.

Run it once, when the freeze is set up. Never rerun it to make a failing freeze test pass: a
failure means the generator changed the old levels, which is the bug.

It also freezes the iteration-2 suites (`--iteration2`: configs/iteration2/level_suites.toml,
cached in results/iteration2/levels/, written to tests/data/v4_level_hashes.json), before any run
(Shannyn, 2026-11-15). It prints only counts, never anything about a level's content, so the
held-out suite stays unopened.

Usage:
    uv run python scripts/freeze_level_hashes.py
    uv run python scripts/freeze_level_hashes.py --iteration2
"""

import argparse
import json
import sys
from pathlib import Path

from stereo_flyness.game import suites
from stereo_flyness.game.generator import BUILDERS
from stereo_flyness.game.level import Level

ROOT = Path(__file__).resolve().parents[1]
SETS = {
    "iteration1": (ROOT / "configs" / "level_suites.toml", ROOT / "results" / "levels",
                   ROOT / "tests" / "data" / "v3_level_hashes.json"),
    "iteration2": (ROOT / "configs" / "iteration2" / "level_suites.toml", ROOT / "results" / "iteration2" / "levels",
                   ROOT / "tests" / "data" / "v4_level_hashes.json"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iteration2", action="store_true", help="freeze the iteration-2 suites instead")
    CONFIG, CACHE, OUT = SETS["iteration2" if parser.parse_args().iteration2 else "iteration1"]
    config = suites.load_config(CONFIG)
    frozen, problems = {}, []
    for job in suites.jobs(config):
        row = suites.load_row(CACHE, job)
        cached = Level.load(CACHE / job.suite / f"{job.name}.json")
        attempt = row["attempts"] - 1
        rebuilt = BUILDERS[job.kind](job.seed, job.difficulty, config["seconds"], attempt,
                                     version=job.generator_version)
        h = suites.level_hash(cached)
        if suites.level_hash(rebuilt) != h:
            problems.append(job.name)
        frozen[f"{job.suite}/{job.name}"] = {"generator_version": job.generator_version,
                                             "attempt": attempt, "sha256": h}
    if problems:
        print(f"{len(problems)} cached levels don't match a rebuild, nothing written: {problems}")
        return 1
    OUT.write_text(json.dumps({"seconds": config["seconds"], "levels": frozen}, indent=1) + "\n")
    print(f"{len(frozen)} levels rebuild identically; wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
