"""Run recording (R1, D19): log every tick of a run so it can be replayed, measured and audited.

A `RunLog` is filled one tick at a time with `log.append(game, held)`, from any loop: `play` below,
the bot's search, or the brain's `run_frames` callback. It's saved as a folder:
    ticks.parquet   one row per tick (columns in COLUMNS)
    summary.json    the run's outcome (RunSummary)

Replaying the logged `held` column through a fresh `Game` reproduces the run exactly (the engine is
deterministic), so a log is also a full record of the inputs.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from stereo_flyness.game.engine import Game

COLUMNS = ["tick", "time", "x", "y", "vy", "mode", "held", "on_ground", "events"]


@dataclass
class RunSummary:
    level: str
    completed: bool
    progress: float  # fraction of the level's length reached (0 to 1)
    ticks: int
    seconds: float
    jumps: int
    death_kind: str | None = None
    death_source_id: int | None = None
    death_x: float | None = None
    death_y: float | None = None

    @classmethod
    def of(cls, game: Game, jumps: int) -> "RunSummary":
        d = game.death
        return cls(
            level=game.level.name, completed=game.finished, progress=game.progress,
            ticks=game.ticks, seconds=game.time, jumps=jumps,
            death_kind=d.kind if d else None, death_source_id=d.source_id if d else None,
            death_x=d.x if d else None, death_y=d.y if d else None,
        )


class RunLog:
    def __init__(self, level_name: str):
        self.level_name = level_name
        self.rows: list[tuple] = []
        self.summary: RunSummary | None = None

    def append(self, game: Game, held: bool) -> None:
        """Record the state right after `game.tick(held)`."""
        p = game.player
        self.rows.append((game.ticks, game.time, p.x, p.y, p.vy, p.mode, held, p.on_ground,
                          ";".join(game.events)))

    def finish(self, game: Game) -> RunSummary:
        jumps = sum("jump" in r[-1].split(";") for r in self.rows)
        self.summary = RunSummary.of(game, jumps)
        return self.summary

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=COLUMNS)

    def save(self, folder: Path) -> None:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.to_frame().to_parquet(folder / "ticks.parquet", index=False)
        (folder / "summary.json").write_text(json.dumps(asdict(self.summary), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, folder: Path) -> "RunLog":
        folder = Path(folder)
        summary = RunSummary(**json.loads((folder / "summary.json").read_text(encoding="utf-8")))
        log = cls(summary.level)
        log.rows = list(pd.read_parquet(folder / "ticks.parquet").itertuples(index=False, name=None))
        log.summary = summary
        return log


def play(game: Game, policy: Callable[[Game], bool], max_ticks: int = 1_000_000) -> RunLog:
    """Run `game` to the end (or `max_ticks`), asking `policy(game)` for the button each tick."""
    log = RunLog(game.level.name)
    while not game.over and game.ticks < max_ticks:
        held = bool(policy(game))
        game.tick(held)
        log.append(game, held)
    log.finish(game)
    return log
