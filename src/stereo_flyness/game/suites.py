"""Practice-level suites (D26): seeds in configs/level_suites.toml, levels cached in results/levels/.

Each job is (suite, kind, difficulty, seed). Building a job generates the level (bot-validated),
measures its difficulty, and writes three files to `<out>/<suite>/`:
    <name>.json        the level (docs/level_format.md)
    <name>.bot.txt     the bot's winning per-frame inputs ("0"/"1"), for replay
    <name>.meta.json   generator version, attempts and difficulty statistics

A job whose meta file already exists with the current generator version is skipped, so suites are
built once and reused.
"""

import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from stereo_flyness.game.bot import BotResult
from stereo_flyness.game.difficulty import measure
from stereo_flyness.game.generator import BUILDERS, GENERATOR_VERSION, generate
from stereo_flyness.game.level import Level

KINDS = tuple(BUILDERS)  # cube, ship, mixed
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Job:
    suite: str
    kind: str
    difficulty: str
    seed: int

    @property
    def name(self) -> str:
        return f"{self.kind}-{self.difficulty}-{self.seed}"


def load_config(path: Path) -> dict:
    config = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("generator_version") != GENERATOR_VERSION:
        raise ValueError(f"{path} is for generator v{config.get('generator_version')}, "
                         f"but the code is v{GENERATOR_VERSION}. Update the config deliberately.")
    return config


def jobs(config: dict, suite: str | None = None, limit: int | None = None) -> list[Job]:
    """All jobs in the config (or one suite), optionally capped at `limit` per kind and difficulty."""
    out = []
    for name, spec in config["suites"].items():
        if suite and name != suite:
            continue
        for kind in KINDS:
            for difficulty, count in spec.get(kind, {}).items():
                n = count if limit is None else min(count, limit)
                out += [Job(name, kind, difficulty, spec["first_seed"] + i) for i in range(n)]
    return out


def _paths(out_dir: Path, job: Job) -> tuple[Path, Path, Path]:
    base = Path(out_dir) / job.suite / job.name
    return base.with_suffix(".json"), base.with_suffix(".bot.txt"), base.with_suffix(".meta.json")


def is_built(out_dir: Path, job: Job) -> bool:
    meta = _paths(out_dir, job)[2]
    return meta.exists() and json.loads(meta.read_text())["generator_version"] == GENERATOR_VERSION


def build(job: Job, out_dir: Path, seconds: float) -> dict:
    """Generate, validate, measure and save one level. Returns its manifest row."""
    level_path, bot_path, meta_path = _paths(out_dir, job)
    level_path.parent.mkdir(parents=True, exist_ok=True)
    g = generate(job.kind, job.seed, job.difficulty, seconds)
    stats = measure(g.level, g.bot.tick_inputs)
    g.level.save(level_path)
    bot_path.write_text("".join("1" if h else "0" for h in g.bot.frame_inputs))
    windows = stats.windows_ms
    row = {
        **asdict(job), "name": job.name, "generator_version": GENERATOR_VERSION,
        "attempts": g.attempts, "bot_nodes": g.bot.nodes,
        "seconds": round(stats.seconds, 2), "hazards": stats.hazards, "solids": stats.solids,
        "clusters_per_10s": round(stats.clusters_per_10s, 2),
        "median_gap_s": _round(stats.median_gap_s), "min_gap_s": _round(stats.min_gap_s),
        "presses": stats.presses, "tightest_window_ms": _round(stats.tightest_window_ms, 1),
        "median_window_ms": _round(stats.median_window_ms, 1),
        "pct_windows_under_50ms": round(100 * sum(w < 50 for w in windows) / len(windows), 1) if windows else None,
        "tightest_opening": stats.tightest_opening,
    }
    meta_path.write_text(json.dumps(row, indent=1))
    return row


def _round(v, digits=3):
    return None if v is None else round(v, digits)


def load_row(out_dir: Path, job: Job) -> dict:
    return json.loads(_paths(out_dir, job)[2].read_text())


def load_level(out_dir: Path, job: Job) -> tuple[Level, BotResult]:
    """A built level and the bot's winning run (for replays and comparisons with the fly)."""
    level_path, bot_path, _ = _paths(out_dir, job)
    level = Level.load(level_path)
    frames = [c == "1" for c in bot_path.read_text().strip()]
    return level, BotResult(True, frames, frame_ticks=4, nodes=0, farthest_x=level.length)
