"""The write-up's figures R2, R4, R6 and R8 (docs/notes/writeup_results.md), drawn only from the
results files the reports already made. Nothing is computed here that a report doesn't already
state; every figure shows each level or run as a dot, so nothing is hidden behind an average.

- R2: cube progress per held-out level: the fly of record (median of seeds 0-2), never press,
  random presses (mean of 10 draws) and the ideal 39° fly (collision course). Step 2, D48.
- R4: progress per held-out level for each Step 4 network, intact first (median over seeds). D51.
- R6: ship progress per held-out level for B, corrected signs, B90 and C (median run). D53.
- R8: Stereo Madness progress per run, per variant, over its cube and ship sections. D54.

Writes PNGs to results/figures/ (git-ignored: R8 is drawn from Stereo Madness, D9).

Usage (matplotlib isn't a project dependency):
    uv run --with matplotlib python scripts/make_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from stereo_flyness.game.level import Level  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "figures"

# Light theme; categorical slots in fixed order (checked: CVD-separable, labels carry identity).
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]  # a second cue besides colour

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
    "text.color": INK, "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})


def pct(s):
    return 100 * s


def short(level: str) -> str:
    """cube-easy-1000003 -> easy 3."""
    parts = level.split("-")
    return f"{parts[1]} {int(parts[2]) % 1000}" if len(parts) == 3 else level


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {(OUT / name).relative_to(ROOT)}")


def level_dots(ax, table: pd.DataFrame, columns: list[str], labels: list[str]):
    """One row per level, one dot per setting, levels in the table's order."""
    y = list(range(len(table)))
    k = len(columns)
    for i, (col, lab) in reversed(list(enumerate(zip(columns, labels)))):  # the fly drawn last, on top
        dy = 0.16 * (i - (k - 1) / 2)  # each setting on its own line within the row, so none hides another
        ax.scatter(table[col], [v + dy for v in y], s=26, color=SERIES[i], marker=MARKERS[i], label=lab,
                   zorder=3 + k - i, edgecolors=SURFACE, linewidths=0.7)
    handles, names = ax.get_legend_handles_labels()
    ax.set_yticks(y, [short(lv) for lv in table.index])
    ax.invert_yaxis()
    ax.set_xlim(-2, 102)
    ax.set_xlabel("progress (%)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles[::-1], names[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
              fontsize=8)


def fig_r2():
    runs = pd.read_csv(RES / "step2" / "final_held_out_runs.csv")
    refs = pd.read_csv(RES / "references" / "final_held_out.csv")
    ideal = pd.read_csv(RES / "ideal_fly" / "held_out20.csv")
    fly = runs[runs["setting"] == "baseline"].groupby("level")["progress"].median()
    t = pd.DataFrame({
        "fly": fly,
        "never": refs[refs["reference"] == "never press"].set_index("level")["progress"],
        "random": refs[refs["reference"] == "random presses"].groupby("level")["progress"].mean(),
        "ideal": ideal[ideal["mode"] == "collision"].set_index("level")["progress"],
    }).apply(pct)
    t = t.sort_values(["fly", "ideal"], ascending=False)
    fig, ax = plt.subplots(figsize=(6.4, 6.2))
    level_dots(ax, t, ["fly", "ideal", "random", "never"],
               ["fly of record (median of 3 seeds)", "ideal 39° fly", "random presses (mean of 10)", "never press"])
    ax.set_title("R2. The untuned fly on 20 held-out cube levels", loc="left", pad=42)
    save(fig, "R2_cube_progress.png")


def fig_strips(df, group_col, order, value_col, title, name, note=None, figsize=(6.4, 4.2), means=None):
    """One row per condition: every level's value as a dot, the median as a tick. `means` (condition ->
    %) overrides the mean printed, so it's the one the report states."""
    fig, ax = plt.subplots(figsize=figsize)
    for i, cond in enumerate(order):
        v = pct(df.loc[df[group_col] == cond, value_col])
        ax.scatter(v, [i] * len(v), s=22, color=SERIES[0] if i == 0 else MUTED, alpha=0.75, zorder=3,
                   edgecolors=SURFACE, linewidths=0.6)
        ax.plot([v.median()] * 2, [i - 0.32, i + 0.32], color=INK, lw=2, zorder=4)
        mean = v.mean() if means is None else means[cond]
        ax.text(108, i, f"median level {v.median():.0f}%  ·  mean {mean:.1f}%", va="center", fontsize=8,
                color=INK2)
    ax.set_yticks(range(len(order)), order)
    ax.invert_yaxis()
    ax.set_xlim(-2, 102)
    ax.set_xlabel("progress per held-out level (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title(title, loc="left")
    if note:
        fig.text(0.01, -0.02, note, fontsize=7.5, color=MUTED, ha="left", va="top", wrap=True)
    save(fig, name)


def fig_r4():
    runs = pd.read_csv(RES / "step4" / "runs.csv")
    per_level = runs.groupby(["condition", "level"])["progress"].median().reset_index()
    order = ["intact whole brain", "(a) shuffle", "(d) random network", "(b) looming-kept shuffle", "(c) relay-only",
             "E5b (inhibitory partners silenced)", "E5b recruited-matched control", "E5b random lesion",
             "E5c (excitatory partners silenced)", "E5c recruited-matched control", "E5c random lesion"]
    fig_strips(per_level, "condition", order, "progress",
               "R4. Control networks and lesions against the intact brain", "R4_controls_lesions.png",
               note="Each dot is one held-out level (median over seeds 0-2); the black tick is the median level; "
                    "the mean is over all 60 runs, as in the report. Comparisons and p-values: D51 and "
                    "docs/notes/step4_report.md.", figsize=(7.2, 5.0),
               means=pct(runs.groupby("condition")["progress"].mean()))


def fig_r6():
    runs = pd.read_csv(RES / "ship_baseline" / "held_out" / "runs.csv")
    per_level = runs.groupby(["design", "level"])["progress"].median().reset_index()
    names = {"B": "B (record)", "B_corrected": "B, corrected signs", "B90": "B90 (faster anchor)",
             "C": "C (control, no self-motion term)"}
    per_level["design"] = per_level["design"].map(names)
    fig_strips(per_level, "design", list(names.values()), "progress",
               "R6. The ship on 20 held-out levels", "R6_ship_progress.png",
               note="Each dot is one held-out level (median run of seeds 0-2); the black tick is the median level. "
                    "The mean is of the median runs, as in the report. The ideal ship (no brain) completes 14 of 20, "
                    "mean 81.4% (D53 result).")


def fig_r8():
    runs = pd.read_csv(RES / "stereo_madness" / "runs.csv")
    level = Level.load(ROOT / "data" / "gd" / "stereo_madness.json")
    names = {"record": "record (150 Hz)", "r50": "50 Hz (tuned variant)", "corrected": "corrected signs"}
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    for mode, x0, x1, _ in level.sections():
        if mode == "ship":
            ax.axvspan(100 * x0 / level.length, 100 * x1 / level.length, color=GRID, alpha=0.7, lw=0, zorder=0)
    first_ship = 100 * next(x0 for m, x0, *_ in level.sections() if m == "ship") / level.length
    ax.text(first_ship + 0.8, -0.65, "ship sections shaded", fontsize=7.5, color=MUTED, va="bottom")
    for i, (v, lab) in enumerate(names.items()):
        p = pct(runs.loc[runs["variant"] == v, "progress"]).sort_values()
        # identical values sit side by side, not on top of each other
        jitter = p.groupby(p.round(1)).cumcount() - p.groupby(p.round(1)).transform("size").sub(1) / 2
        ax.scatter(p, i + 0.09 * jitter, s=24, color=SERIES[i], marker=MARKERS[i], zorder=3,
                   edgecolors=SURFACE, linewidths=0.6)
        done = int(runs.loc[runs["variant"] == v, "completed"].sum())
        ax.text(103, i, f"{done} of 10 completed · median {p.median():.1f}%", va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(names)), list(names.values()))
    ax.invert_yaxis()
    ax.set_ylim(2.6, -0.8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("progress through Stereo Madness (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("R8. Stereo Madness: every run, per variant (seeds 0-9)", loc="left")
    save(fig, "R8_stereo_madness.png")


def main():
    fig_r2()
    fig_r4()
    fig_r6()
    fig_r8()


if __name__ == "__main__":
    main()
