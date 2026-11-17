# Opening the Stereo Madness new-seed report: reading order

*Jacob, 2026-11-17. Written **before any iteration-2 Stereo Madness run**. Everything that decides a result is already fixed in D60 (`sm_newseeds_plan.md`, `scripts/sm_newseeds_report.py`). This note only sets the order and says where each measure is read, as `fix1_heldout_opening.md` did for the held-out report. It needs Shannyn's OK before the report is opened.*

**What this opening is (D55, D60):** how far the fly gets on Stereo Madness with iteration 2's interface. **It judges nothing:**
- fix 1 was judged by its held-out opening alone, and it counts (D61);
- Part 1's 100 runs are context, not a comparison: they're different seeds and had no fix 1;
- nothing here is tested for significance.

## Before opening

1. **Write the report without reading it:** `uv run python scripts/sm_newseeds_report.py`. It prints only the checks. It exits without writing anything if a check fails:
   - all 100 runs present;
   - settings, seed, fix 1 (ii) and the original connectome right;
   - exact replays;
   - one clean commit;
   - stuck runs counted.
2. **If Part 1's context runs fail their checks,** the script leaves the context out. The milestones and prediction 8's measures then go with it, because both need Part 1's furthest point. **We'd stop and fix that before opening,** rather than open a report that can't score prediction 8.
3. **Checksum** to `results/iteration2/stereo_madness/report_sha256.txt` before opening; check it at the opening.

## Reading order (opened together, ~30 min)

1. **Header and checks** (~2 min): the commit, seeds 100–199, 100 runs, and the stuck-run count.
2. **The headline** (~5 min): completed **k of 100** and the **median progress**, which for N = 100 is the mean of the 50th and 51st runs (#86), with the quartiles and range. This is the line that's quoted. The best run is never the headline.
   - Beside it, in italics: Part 1's 100 runs by the same measures, as context.
3. **Where runs ended** (~5 min): each hazard strip, or else each 30-unit cell, with counts for fix 1 (ii) and for Part 1. Expected landmarks from D54:
   - the double spike at x 2382–2418;
   - the pits after the raised platform, ending at x 2899.5.
4. **Milestones** (~5 min), each with how many runs reach it:
   - past Part 1's furthest point: alive past x 2899.5 + half a cube, or completed (D60, agreed on #87);
   - the first ship portal (~30%);
   - the first ship section cleared;
   - a complete run.
5. **Frames fix 1 changed** (~2 min): how many runs, and frames per run. This is where fix 1 acted. It isn't a measure of success.
6. **Prediction 8** (~3 min), scored below.
7. **The showcase pick** (~3 min): the run closest to the median, ties to the lowest seed (D54's rule). The furthest run is optional, captioned "the furthest of 100". Both are rendered only after this opening, with:
   - D55's exploratory label;
   - fix 1's frame label;
   - our input shown apart from the fly's activity (hard rule 10).

   The pipeline was rehearsed on a held-out run (D61).
8. **Only then, anything else** (~5 min), labelled as interpretation. For example: which replays to watch, and whether any run reached the ship.

## How prediction 8 is scored (D60, unchanged)

Shannyn's fix 1 prediction 8: "Median unchanged at ~9.2%; the furthest run passes 10.9%."

| Part | Read from | Holds if |
|---|---|---|
| Median unchanged | "Measures for Shannyn's fix 1 prediction 8": *median within ±1 point of 9.2%* | The median is in **8.2–10.2%** inclusive |
| The furthest run passes 10.9% | Same section: *a run past Part 1's furthest point* | **At least one run** is alive past the pits ending at x 2899.5, or completed |

**Hit only if both hold.** There's no partial credit, but each part is reported, so a miss shows which part failed.

## After the opening

1. A D-entry with the result. Fill P8 and P9 of `writeup_part2.md`, and mark prediction 8 in `fix1_design.md`.
2. Render the showcase replay (and the labelled furthest run, if we want it). It stays local: Stereo Madness's level design is RobTop's (D9).
3. Then what's left of iteration 2:
   - whether to raise fix 2 (b), whose condition D61 found met and which is undecided;
   - the write-up;
   - the single LinkedIn post at the very end.
