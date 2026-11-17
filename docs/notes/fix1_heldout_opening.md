# Opening the held-out report: reading order and how each prediction is scored

*Jacob, 2026-11-16. Written **while the 360 held-out runs were going, before the report existed**. Everything that decides a result is already fixed: the measures in `fix1_heldout_plan.md`, the code in `scripts/fix1_heldout_report.py` (#82), and Shannyn's predictions in `fix1_design.md` (#85). This note does two things. It sets the order, as for step 3, so the fixed questions are answered before anything is explored. And it says how each prediction is read off the report, so nothing about scoring is decided after the numbers are seen. **The scoring rules below need Shannyn's OK before the report is opened.** Where her wording allows two readings, both are given, with the one I propose.*

## Before opening

1. **The report is written without being read:** `uv run python scripts/fix1_heldout_report.py`, without `--show`. It exits with a list of problems if any check fails, and then nothing is reported. The checks are:
   - all 360 runs present, with the right settings;
   - one clean commit;
   - exact replays;
   - the arms identical up to the first frame fix 1 changed;
   - stuck runs counted.
2. **Checksum:** write `results/iteration2/fix1_heldout_report_sha256.txt` before opening, and check it at the opening.
3. **This note is agreed and merged first,** so the scoring is fixed in the repo before the report is opened.

## Reading order (opened together, ~45 min)

1. **Header and checks** (~2 min). The commit should be `17d552e`. Since the report exists, every check passed.
2. **Section 1, the test** (~15 min):
   1. the levels with a fix-case drop, and how many were left out;
   2. better / worse / tied, and p: **the test, passed or not**;
   3. the changed-frames line;
   4. by k, then each level's feature;
   5. then the shared tables: drops by k, pit width, plain step-downs, progress, completions, deaths.
3. **Section 2, the no-harm check** (~10 min):
   1. better / worse / tied on obstacles passed, and p;
   2. (a) and (b): **the check, passed or not**;
   3. the levels fix 1 changed, with what happened;
   4. the shared tables;
   5. last, the side check: the fresh unfixed runs against Part 1, tick for tick. It's reported, not used to judge.
4. **Verdict** (~3 min): the test, the check, and fix 1's own condition. **Fix 1 counts or doesn't.** No revision follows either way (D55 rule d, D57).
5. **Predictions, hit or miss** (~10 min), by the rules below, one line each.
6. **Only then, anything else** (~5 min): what surprised us, labelled as interpretation.

## How each prediction is scored

Hit or miss, no partial credit, bounds inclusive. "Fix-case drops reached" are the test suite's: iteration 1's levels have no fix-case drops.

| # | Prediction (Shannyn) | Read from | Hit if |
|---|---|---|---|
| **7** | Real fly, iteration-2 held-out: does fix 1 pass the bar? **Yes** (`fix1_design.md`) | Verdict | **Proposed:** the verdict says "Fix 1 counts", which needs the test, the no-harm check and fix 1's own condition. *Other reading:* section 1's test alone. I propose the verdict, because D55's bar is "a fix counts", and both plans score prediction 7 as "does fix 1 pass the bar". |
| H1 | The test: fixed better on **≥ 8** levels, worse on **≤ 1** | Section 1, better / worse | Both hold. |
| H2 | Fix-case drops reached, share cleared: **unfixed ≤ 5%; fixed 40–65%** | Section 1, "Every drop reached, by k", fix rows summed over k, per arm | Both hold. If the unfixed arm reaches no fix-case drop, its half is unscorable and the prediction is reported as such. |
| H3 | Fix-case drops with **k = 2**, share cleared with the fix: **≤ 10%** | Section 1, fix row, k = 2, fix 1 (ii) | It holds. Unscorable if no k = 2 drop is reached. |
| H4 | No-harm check **passes both parts** | Section 2, (a) and (b) | Both say yes. |
| H5 | Iteration-1 held-out levels that **tie exactly** (same obstacles passed in both arms): **≥ 15 of 20** | Section 2, "tied" | **Proposed:** the tied count on each level's score (the median obstacle groups passed), as her parenthesis defines it. *Other reading:* levels where all 3 seeds play identically in both arms (20 minus the levels fix 1 changed). It's given beside the score, for the record. |
| H6 | Levels where fix 1 changed no frame: **every one plays identically** in both arms | The checks | **It can't miss once the report exists:** the report refuses to run otherwise. Proposed: record it as "held (a check)", and count it separately from the hits and misses rather than in the tally. |
| H7 | Jumps while on top of a plain step-down, both suites: **no more with the fix** | Verdict, fix 1's own condition | Fixed ≤ unfixed. |

**Recorded after the opening:**
- in fix1_design.md, beside each prediction;
- in a D-entry;
- in P5 and P9 of `writeup_part2.md`, with the tally given as "__ of 7 scored (+ H6, a check that held)".

Prediction 8 (Stereo Madness) waits for the new-seed runs.

## After the opening

1. The D-entry for the held-out result. Fill P5 and P9 of `writeup_part2.md`, and M6's commit in `writeup_methods_part2.md` if it changed.
2. **The Stereo Madness runs** (D60, #87). They need #86 and #87 merged and this checkout clean and on main. They may run before or after this opening (the plan allows either). They run from a clean commit after the held-out runs end.
