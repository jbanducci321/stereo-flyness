"""Running a batch of closed-loop runs so that a broken worker pool doesn't stop it.

On Windows, joblib's worker pool sometimes breaks mid-batch (`BrokenProcessPool`, from `WinError 6:
the handle is invalid`; seen twice on 2026-11-11). A run's files are written only when it ends, with
run.json last (`FlyRecorder.save`), so a run either finished or left nothing usable. Two tools:

- `play_with_retries`: retry, in a fresh pool, the runs of this call that didn't finish.
- `resumable`: for `--resume`, the levels still to play after a whole batch was killed (e.g. a
  restart), refusing if any finished run is from another commit, so a batch never mixes commits.
"""

import json
from pathlib import Path

from joblib.externals.loky.process_executor import BrokenProcessPool

POOL_ERRORS = (BrokenProcessPool, OSError)
TRIES = 3


def play_with_retries(names, play_batch, tries: int = TRIES, log=print) -> list[dict]:
    """Play `names` with `play_batch(names)`, which yields one summary per finished run (with its
    "level"). If the pool breaks, play the ones without a summary again, up to `tries` times in all.
    Raises the last error if some still haven't finished."""
    done: dict[str, dict] = {}
    todo = list(names)
    for attempt in range(1, tries + 1):
        try:
            for s in play_batch(todo):
                done[s["level"]] = s
            return [done[n] for n in names]
        except POOL_ERRORS as e:
            todo = [n for n in names if n not in done]
            if attempt == tries:
                raise
            log(f"worker pool broke ({type(e).__name__}: {e}); retrying {len(todo)} unfinished "
                f"run{'s' if len(todo) != 1 else ''} in a new pool (try {attempt + 1}/{tries})")
    raise AssertionError("unreachable")


def resumable(names, run_dir, commit: str) -> tuple[list[str], list[str]]:
    """(to play, already done) for `--resume`: a level is done if `run_dir/<level>/run.json` exists.
    Refuses (ValueError) if a done run was made at another commit, or the current tree is dirty."""
    if commit.endswith("-dirty"):
        raise ValueError("--resume needs a clean tree: a -dirty run can't be matched to its code")
    todo, done = [], []
    for n in names:
        p = Path(run_dir) / n / "run.json"
        if not p.exists():
            todo.append(n)
            continue
        made = json.loads(p.read_text(encoding="utf-8")).get("commit")
        if made != commit:
            raise ValueError(f"{n} was run at {str(made)[:12]}, not the current {commit[:12]}; "
                             "move those runs away or run without --resume")
        done.append(n)
    return todo, done
