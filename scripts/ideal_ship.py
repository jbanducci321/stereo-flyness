"""Ideal ships (Shannyn's §1d and §8 checks, docs/notes/ship_ideal.md): can a ship encoding fly the
training ship levels at all, with no brain?

Each ideal ship uses a ship encoding (`ShipEncoder`) and the draft output rule, with "the pooled motion
is downward" in place of "a DNp22 spike": after each tick, downward motion releases the next tick,
anything else holds it (sign only, so no threshold to pick). Never hold and always hold run beside them.
- Round 1 (§1d): full geometry (both motion terms) and self-motion only.
- Round 2 (§8): option B (self-motion relative to the speed that reaches the next opening), option C
  (steering only) and self-motion only, judged by §8d's bars.

Training ship levels only: never held-out levels, never Stereo Madness (hard rule 5).

Usage:
    uv run python scripts/ideal_ship.py              # round 1
    uv run python scripts/ideal_ship.py --round 2    # round 2

Writes results/ideal_ship/training.csv and .md (round 2: training_round2.*; git-ignored).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import LEVELS, job
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.ship_encoding import ShipEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "ideal_ship"
SUITE = "training"
DIFFICULTIES = ("easy", "medium", "hard")
BAR = 0.5  # share of easy levels completed (Shannyn, 2026-11-10)
NO_NEURONS = {t: {s: [] for s in ("right", "left")} for t in ("T4c", "T4d", "T5c", "T5d")}
TERMS = {"full geometry": "full", "self-motion only": "self", "B (relative to the target)": "B",
         "C (steering only)": "C"}
ROUNDS = {1: ("full geometry", "self-motion only"),
          2: ("B (relative to the target)", "C (steering only)", "self-motion only")}
REFERENCES = ("never hold", "always hold")


def player_rule(name, level):
    if name == "never hold":
        return lambda game: False
    if name == "always hold":
        return lambda game: True
    enc = ShipEncoder(level, NO_NEURONS, rate_hz=0.0, terms=TERMS[name])
    return lambda game: enc.encode(game.player, game.bounds).omega_deg >= 0  # downward -> release


def play(level, rule) -> dict:
    """One game: `rule(game)` after each tick decides whether the next tick is held (ship mode only)."""
    game, held = Game(level), False
    ship_ticks = held_ticks = floor_ticks = ceiling_ticks = 0
    while not game.over:
        game.tick(held)
        p = game.player
        held = p.mode == "ship" and rule(game)
        if p.mode == "ship":
            ship_ticks += 1
            held_ticks += held
            floor, ceiling = game.bounds
            floor_ticks += p.bottom <= floor + 1e-6
            ceiling_ticks += p.top >= ceiling - 1e-6
    d = game.death
    n = max(ship_ticks, 1)
    return {"completed": game.finished, "progress": round(game.progress, 3),
            "death": None if d is None else f"{d.kind} at x {d.x:.0f}, y {d.y:.0f}",
            "held_share": round(held_ticks / n, 3), "on_floor_share": round(floor_ticks / n, 3),
            "at_ceiling_share": round(ceiling_ticks / n, 3)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--round", type=int, default=1, choices=sorted(ROUNDS))
    rnd = ap.parse_args().round
    players = ROUNDS[rnd] + REFERENCES
    tag = SUITE if rnd == 1 else f"{SUITE}_round{rnd}"
    sys.stdout.reconfigure(encoding="utf-8")
    names = sorted((p.stem for p in (LEVELS / SUITE).glob("ship-*.json") if not p.stem.endswith(".meta")),
                   key=lambda n: (DIFFICULTIES.index(n.split("-")[1]), int(n.split("-")[2])))
    rows = []
    for name in names:
        level, _ = load_level(LEVELS, job(name, SUITE))
        for who in players:
            rows.append({"level": name, "difficulty": name.split("-")[1], "player": who, **play(level, player_rule(who, level))})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{tag}.csv", index=False)

    lines = [f"# Ideal ships, round {rnd}: {len(names)} training ship levels\n",
             "No brain: a ship encoding with a sign-only rule (downward motion releases the next tick). Not a model result.\n",
             "## Completed, by difficulty\n",
             "| Player | " + " | ".join(DIFFICULTIES) + " | Mean progress | Held | On floor | At ceiling |",
             "|---|" + "---|" * (len(DIFFICULTIES) + 4)]
    for who in players:
        g = df[df["player"] == who]
        cells = [f"{int(g.loc[g['difficulty'] == d, 'completed'].sum())}/{int((g['difficulty'] == d).sum())}" for d in DIFFICULTIES]
        lines.append(f"| {who} | " + " | ".join(cells) + f" | {100 * g['progress'].mean():.1f}% | "
                     f"{100 * g['held_share'].mean():.0f}% | {100 * g['on_floor_share'].mean():.0f}% | "
                     f"{100 * g['at_ceiling_share'].mean():.0f}% |")
    lines += ["", "Held, on floor and at ceiling: mean share of ship-mode ticks.", "", "## The bars\n"]
    for who in ROUNDS[rnd][:2]:
        g = df[(df["player"] == who) & (df["difficulty"] == "easy")]
        share = g["completed"].mean()
        lines.append(f"- **{who}:** {int(g['completed'].sum())}/{len(g)} easy levels ({share:.0%}), bar ≥ 50%: "
                     f"**{'reaches' if share >= BAR else 'does not reach'} the bar**.")
    if rnd == 2:
        done = {w: int(df.loc[df["player"] == w, "completed"].sum()) for w in ROUNDS[2]}
        b, s = done[ROUNDS[2][0]], done["self-motion only"]
        lines.append(f"- **B against self-motion only** (§8d): {b} against {s} of {len(names)} levels: "
                     f"**{'B completes more' if b > s else 'B does not complete more'}**.")
    lines += ["", "## Every run\n", md_table(df.drop(columns="difficulty"), 3)]
    (OUT / f"{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:lines.index("## Every run\n")]))
    print(f"Wrote {(OUT / tag).relative_to(ROOT)}.csv and .md")


if __name__ == "__main__":
    main()
