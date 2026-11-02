"""Check the cube encoding (D41) on real levels, with no brain: the cube follows the bot's path.

For each tick, the game state before the tick is encoded (D40: tick i sets brain frame i's
input) and logged: θ, the gap and obstacle, f, and how many neurons of each population would be
driven. Then, for every jump the bot made, it reports θ at the press, and where a fly with a
fixed angular threshold would have pressed instead.

These runs are **bot-driven**: the bot controls the cube, not the fly (hard rule 10). The output
says so in every file.

Usage:
    uv run python scripts/inspect_encoding.py cube-easy-0 cube-medium-0 cube-hard-0
    uv run python scripts/inspect_encoding.py cube-easy-0 --theta-full 180 --mode all

Writes results/encoding/<theta_full>_<mode>/<level>.csv and summary.md (git-ignored).
"""

import argparse
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_pathway_tests import md_table
from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import Job, load_level
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / "results" / "levels"
OUT = ROOT / "results" / "encoding"
THRESHOLD_DEG = 39.0  # the fly's mean short-mode threshold (D43)


def job(name: str, suite: str) -> Job:
    kind, difficulty, seed = name.split("-")
    return Job(suite, kind, difficulty, int(seed))


def bot_run(enc: CubeEncoder, level, inputs) -> pd.DataFrame:
    game, rows = Game(level), []
    for tick, held in enumerate(inputs):
        if game.over:
            break
        p = game.player
        loom = enc.encode(p)
        o = loom.obstacle
        rows.append({"tick": tick, "x": p.x, "y": p.y, "mode": p.mode, "on_ground": p.on_ground,
                     "theta_deg": loom.theta_deg, "gap": loom.gap, "f": loom.f,
                     "obstacle_x0": None if o is None else o.x0, "obstacle_bottom": None if o is None else o.bottom,
                     "obstacle_top": None if o is None else o.top,
                     **{f"driven_{s}_{t}": n for (s, t), n in loom.driven.items()},
                     "bot_held": held, "driver": "bot"})
        game.tick(held)
        rows[-1]["events"] = ";".join(game.events)
    return pd.DataFrame(rows)


def threshold_fly(enc: CubeEncoder, level, threshold: float) -> dict:
    """An ideal fly with no brain: it presses on every tick after one where θ >= `threshold`
    (one tick late, as in D40/D42). A check of the encoding and threshold, not a model result."""
    game, held, presses, trace = Game(level), False, 0, []
    while not game.over:
        game.tick(held)
        p = game.player
        loom = enc.encode(p)
        held = p.mode == "cube" and loom.theta_deg >= threshold
        presses += held
        trace.append((game.ticks, p.x, p.y, p.vy, p.on_ground, None if loom.obstacle is None else loom.obstacle.x0,
                      loom.theta_deg, held))
    d = game.death
    return {"completed": game.finished, "progress": game.progress, "ticks_pressed": presses,
            "death": None if d is None else f"{d.kind} at x {d.x:.0f}", "mode_at_end": game.player.mode,
            "cause": None if d is None else death_cause(level, d, pd.DataFrame(trace, columns=[
                "tick", "x", "y", "vy", "on_ground", "obstacle_x0", "theta", "held"]), threshold)}


INVISIBLE, WRONG_MOMENT = "(a) invisible to the encoding", "(b) visible, but the threshold is the wrong moment"
SHORT_RUN_UP = "(c) short run-up"


def death_cause(level, death, trace: pd.DataFrame, threshold: float) -> str:
    """Why the ideal fly died, from the object that killed it (its visual cell) and what the
    encoding showed on the way there. Starts with the class: (a) the object never loomed,
    (c) it was already at or past `threshold` when it started looming (after a landing or a
    staircase step), so no response "at the threshold" was possible, or (b) it loomed from
    below `threshold`, but pressing there didn't clear it (D44, D45)."""
    hits = [b for b in level.boxes if b.kind == death.kind and not (
        death.x + 15 < b.x0 or b.x1 < death.x - 15 or death.y + 15 < b.y0 or b.y1 < death.y - 15)]
    if not hits:
        return "unknown (no matching object)"
    b = min(hits, key=lambda b: abs((b.x0 + b.x1) / 2 - death.x) + abs((b.y0 + b.y1) / 2 - death.y))
    cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
    cell_x0, bottom, top = round(cx - 15, 6), cy - 15, cy + 15
    recent = trace[trace["tick"] > death.tick - 480]  # the last 2 s
    seen = recent[recent["obstacle_x0"].round(6) == cell_x0]
    where = f"{b.kind} cell x {cell_x0:.0f}, y {bottom:.0f}-{top:.0f}"
    if seen.empty:
        reached = trace[trace["x"] + 15 >= cell_x0]
        at = reached.iloc[0] if len(reached) else trace.iloc[-1]
        if at["y"] - 15 >= top - 1e-6:
            return f"{INVISIBLE}: never loomed; below the cube when reached, landed onto from above ({where})"
        if at["y"] + 15 <= bottom + 1e-6:
            return f"{INVISIBLE}: never loomed; above the cube when reached ({where})"
        return f"{INVISIBLE}: never loomed ({where})"
    if seen["theta"].iloc[0] >= threshold:
        return (f"{SHORT_RUN_UP}: already {seen['theta'].iloc[0]:.0f}° when it started looming "
                f"(gap {cell_x0 - seen['x'].iloc[0] - 15:.0f}) ({where})")
    over = seen[seen["theta"] >= threshold]
    if over.empty:
        return f"{WRONG_MOMENT}: loomed but stayed under {threshold:g}° (max {seen['theta'].max():.0f}°) ({where})"
    ground = over[over["on_ground"]]
    if ground.empty:
        return f"{WRONG_MOMENT}: reached {threshold:g}° only while airborne, so no jump was possible ({where})"
    return f"{WRONG_MOMENT}: jumped at {threshold:g}° but still hit it ({where}; jump at gap {cell_x0 - ground['x'].iloc[0] - 15:.0f})"


def jumps(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Every bot jump in cube mode, with θ at the press and where a θ-threshold fly would press."""
    out = []
    for i in np.flatnonzero(df["events"].str.contains("jump") & (df["mode"] == "cube")):
        row = df.iloc[i]
        approach = df[(df["obstacle_x0"] == row["obstacle_x0"]) & (df.index <= i + 200)]
        hit = approach[approach["theta_deg"] >= threshold]
        out.append({"tick": int(row["tick"]), "x": row["x"], "obstacle_x0": row["obstacle_x0"],
                    "obstacle_height": None if pd.isna(row["obstacle_top"]) else row["obstacle_top"] - row["obstacle_bottom"],
                    "theta_at_press": row["theta_deg"], "gap_at_press": row["gap"],
                    "threshold_tick": None if hit.empty else int(hit["tick"].iloc[0]),
                    "threshold_minus_bot_ms": None if hit.empty else
                    (hit["tick"].iloc[0] - row["tick"]) * 1000 / 240})
    return pd.DataFrame(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="+", help="level names, e.g. cube-easy-0")
    parser.add_argument("--suite", default="training")
    parser.add_argument("--theta-full", type=float, default=180.0, help="degrees (D43 calibrates it)")
    parser.add_argument("--rate", type=float, default=150.0, help="R, Hz")
    parser.add_argument("--mode", default="collision", choices=["collision", "all"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])  # P5's patch order (D41)
    out = OUT / f"{args.theta_full:g}deg_{args.mode}"
    out.mkdir(parents=True, exist_ok=True)

    lines = [f"# Cube encoding on bot-driven runs (θ_full = {args.theta_full:g}°, R = {args.rate:g} Hz, "
             f"mode = {args.mode})\n",
             "**Bot-driven:** the bot controls the cube; no brain is involved. θ is what the fly would see.\n",
             f"Patch sizes per side: " + ", ".join(f"{s} {t} {len(patches[s][t])}" for s in patches for t in patches[s]) + "\n"]
    for name in args.levels:
        level, bot = load_level(LEVELS, job(name, args.suite))
        enc = CubeEncoder(level, patches, args.theta_full, args.rate, args.mode)
        df = bot_run(enc, level, bot.tick_inputs)
        df.to_csv(out / f"{name}.csv", index=False)
        j = jumps(df, THRESHOLD_DEG)
        cube = df[df["mode"] == "cube"]
        looming = cube[cube["theta_deg"] > 0]
        lines += [f"## {name}\n",
                  f"- {len(df)} ticks ({len(df) / 240:.1f} s); cube ticks with something looming: "
                  f"{100 * len(looming) / max(1, len(cube)):.0f}%; whole population driven (f = 1): "
                  f"{100 * (cube['f'] >= 1).mean():.0f}% of cube ticks.",
                  f"- θ while looming: median {looming['theta_deg'].median():.1f}°, 90th percentile "
                  f"{looming['theta_deg'].quantile(0.9):.1f}°, max {looming['theta_deg'].max():.1f}°."]
        if len(j):
            lines += [f"- **{len(j)} bot jumps.** θ at the bot's press: median {j['theta_at_press'].median():.1f}° "
                      f"(range {j['theta_at_press'].min():.1f}–{j['theta_at_press'].max():.1f}°). A fly pressing at "
                      f"{THRESHOLD_DEG:g}° would press a median {j['threshold_minus_bot_ms'].median():+.0f} ms after the bot "
                      "(negative = earlier).", ""]
            lines.append(md_table(j, 1))
        ideal = threshold_fly(enc, level, THRESHOLD_DEG)
        lines += ["", f"- **Ideal {THRESHOLD_DEG:g}° fly** (no brain; presses whenever θ ≥ {THRESHOLD_DEG:g}°, "
                  "one tick late): " + ("**completes the level**" if ideal["completed"] else
                                         f"dies at {100 * ideal['progress']:.0f}% ({ideal['death']}). "
                                         f"Cause: {ideal['cause']}") + "."]
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
