"""The two ideal ships (Shannyn's §1d check, docs/notes/ship_ideal.md): can the draft motion encoding
fly the training ship levels at all, with no brain?

Each ideal ship uses the draft encoding (`ShipEncoder`) and output rule, with "the pooled motion is
downward" in place of "a DNp22 spike": after each tick, downward motion releases the next tick,
anything else holds it (sign only, so no threshold to pick). One uses both motion terms ("full"),
one the ship's own climb and fall only ("self"). Never hold and always hold run next to them.

Training ship levels only: never held-out levels, never Stereo Madness (hard rule 5).

Usage:
    uv run python scripts/ideal_ship.py

Writes results/ideal_ship/training.csv and .md (git-ignored).
"""

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
PLAYERS = ("full geometry", "self-motion only", "never hold", "always hold")


def player_rule(name, level):
    if name == "never hold":
        return lambda game: False
    if name == "always hold":
        return lambda game: True
    enc = ShipEncoder(level, NO_NEURONS, rate_hz=0.0, terms="full" if name == "full geometry" else "self")
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
    sys.stdout.reconfigure(encoding="utf-8")
    names = sorted((p.stem for p in (LEVELS / SUITE).glob("ship-*.json") if not p.stem.endswith(".meta")),
                   key=lambda n: (DIFFICULTIES.index(n.split("-")[1]), int(n.split("-")[2])))
    rows = []
    for name in names:
        level, _ = load_level(LEVELS, job(name, SUITE))
        for who in PLAYERS:
            rows.append({"level": name, "difficulty": name.split("-")[1], "player": who, **play(level, player_rule(who, level))})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{SUITE}.csv", index=False)

    lines = [f"# The two ideal ships: {len(names)} training ship levels\n",
             "No brain: the draft encoding with a sign-only rule (downward motion releases the next tick). Not a model result.\n",
             "## Completed, by difficulty\n",
             "| Player | " + " | ".join(DIFFICULTIES) + " | Mean progress | Held | On floor | At ceiling |",
             "|---|" + "---|" * (len(DIFFICULTIES) + 4)]
    for who in PLAYERS:
        g = df[df["player"] == who]
        cells = [f"{int(g.loc[g['difficulty'] == d, 'completed'].sum())}/{int((g['difficulty'] == d).sum())}" for d in DIFFICULTIES]
        lines.append(f"| {who} | " + " | ".join(cells) + f" | {100 * g['progress'].mean():.1f}% | "
                     f"{100 * g['held_share'].mean():.0f}% | {100 * g['on_floor_share'].mean():.0f}% | "
                     f"{100 * g['at_ceiling_share'].mean():.0f}% |")
    lines += ["", "Held, on floor and at ceiling: mean share of ship-mode ticks.", "", "## The bar (≥ 50% of easy levels)\n"]
    for who in PLAYERS[:2]:
        g = df[(df["player"] == who) & (df["difficulty"] == "easy")]
        share = g["completed"].mean()
        lines.append(f"- **{who}:** {int(g['completed'].sum())}/{len(g)} easy levels ({share:.0%}): "
                     f"**{'reaches' if share >= BAR else 'does not reach'} the bar**.")
    lines += ["", "## Every run\n", md_table(df.drop(columns="difficulty"), 3)]
    (OUT / f"{SUITE}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:lines.index("## Every run\n")]))
    print(f"Wrote {(OUT / SUITE).relative_to(ROOT)}.csv and .md")


if __name__ == "__main__":
    main()
