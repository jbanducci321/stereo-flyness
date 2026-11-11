# Step 4 and Step 7 opening: procedure, Step 7 reading order and verdict sheet

**What actually happened (2026-11-10):** Jacob and Shannyn chose instead to have Jacob's Claude Code session open both reports and judge every fixed question against D51 and D52, then review its verdicts together. The results are in `docs/notes/step4_report.md` and the D51 and D52 entries. The sheet below was not used.

*Jacob, 2026-11-10. Prepared **without opening either report**: every question below comes from D51, D52, `step4_proposal.md` §5 and `step4_opening.md`. The Step 7 report was generated blind on 2026-11-10 (only its checks were printed: all pass at both rates).*

## Procedure (agreed with Shannyn, 2026-11-10)

The opening is **two independent reads**, not one joint session (it replaces "opened together" in `step4_opening.md`, D51 and D52 for this opening only):
1. **Sunday 15 Nov, 8 pm:** Jacob sends Shannyn `results/step4/report.md` and `results/step7/report.md` (git-ignored, so by email or Drive). Neither is opened before then by anyone, Claude included.
2. Each reads alone, in the order below, and fills in a copy of the verdict sheet **before talking**.
3. **Proposed:** each sends their filled sheet to the other by **Sunday 11:59 pm**, so neither read can shift after hearing the other.
4. **Monday 16 Nov, 9–10 am:** compare and settle any difference against the fixed rules (not by preference). Then Jacob fills in `step4_report.md` and the D51 and D52 results; Shannyn reviews.
5. The Step 4 replays (rendered, unwatched) are watched only **after** Monday's comparison.

## Step 7 reading order (after Step 4)

**Open:** `results/step7/report.md`. Everything that decides a reading is fixed in D52.
1. **Checks** (~1 min), for each rate: 60 pairs, every run replayed exactly, settings shared, clean commits. Already passed when generated; confirm. If any fail, stop.
2. **The bar at 150 Hz** (~3 min): identical games (the cube's x, y, vy equal on every tick, same length) in **≥ 57 of 60** pairs: pass or fail.
3. **The bar at 50 Hz** (~3 min): the same.
4. **Every game that split** (~10 min), per pairing: where the state first differs, what was in view, which network pressed, whether the outcome changed.
5. **Described only** (~10 min): per approach up to each pair's first split; same outcome per level (sign test); progress, completions, death classes, first-spike θ, stuck runs, presses per second.
6. **The fixed readings (D52):** a **pass** means the subcircuit's results stand for the whole brain at that rate, in this setting (cube, D47's encoding). A **fail** means the subcircuit's results stay valid as subcircuit results; nothing is rerun.

**Total: about 30 minutes.**

---

## Verdict sheet (copy once per reader)

**Reader:** ______ **Filled in on:** ______ **Sent to the other reader at:** ______

### Step 4 (`results/step4/report.md`, in `step4_opening.md`'s order)

| # | Question (fixed in D51) | Verdict | Note |
|---|---|---|---|
| 1 | Checks: 11 conditions × 60 runs, clean commits, every connectivity file matches its SHA-256, 0 stuck, 0 unclassified | pass / fail | |
| 2 | Intact whole brain against the Step 2 subcircuit baseline (29%, 6/60 completed, 33 (d1)): described | | |
| 3a | (a) degree-preserving shuffle against intact (sign test, p < 0.05) | better / worse / no clear difference | |
| 3d | (d) random network against intact | better / worse / no clear difference | |
| 4b | (b) looming kept: **relay?** (1) progress no clear difference; (2) pooled first-spike θ (no carry-over) within the intact seed range; (3) (d1) share within the same bar | all three pass / "plays about as far, but not the same way" / neither | |
| 4c | (c) relay-only: the same three bars | as above | |
| 5b | E5b: **specific?** differs from intact **and** from its recruited-matched control, p < 0.05, same direction | specific / not specific | |
| 5c | E5c: the same | specific / not specific | |
| 6 | Controls (old random lesions, recruited-matched) against intact | | |
| 7 | Holm family (12): which survive | list | |

Fixed readings to apply: (b) or (c) or E5c doing **better** than intact is the late-threshold effect (Step 3, D49), not "a relay plays better" or "the lesion improved the fly".

### Predictions (`step4_proposal.md` §5): hit or miss

| Prediction | By | Hit / miss | One line |
|---|---|---|---|
| (a) shuffle: worse than intact, plays like never press (or always press if it runs away) | Jacob | | |
| (d) random network: the same | Jacob | | |
| (b) looming kept: earlier jumps (θ below intact), more (d1), progress the same or lower. *Dated note: open loop it fired later (46.6°)* | Shannyn | | |
| (c) relay-only | – | no prediction | |
| E5b: earlier first spike (below ~37°), more (d1), lower progress | Shannyn | | |
| E5c: later first spike, fewer (d1), more (d2), progress the same or higher | Shannyn | | |
| Random lesions: no clear difference | – | | |
| LC4/LPLC2 code check: 0 Giant Fiber spikes, 0 presses | – | | |

### Step 7 (`results/step7/report.md`)

| # | Question (fixed in D52) | Verdict | Note |
|---|---|---|---|
| 1 | Checks at both rates | pass / fail | |
| 2 | 150 Hz: identical games ___ / 60 (bar ≥ 57) | pass / fail | |
| 3 | 50 Hz: identical games ___ / 60 (bar ≥ 57) | pass / fail | |
| 4 | Splits that changed the outcome: 150 Hz ___, 50 Hz ___ | | |
| 5 | Same outcome per level (sign test), both rates: described | | |

### Anything else (interpretation, kept apart from the verdicts)

-
