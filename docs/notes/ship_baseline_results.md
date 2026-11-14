# Ship baseline (Step 5, D53): results

*Jacob, 2026-11-11. The full write-up behind D53's result line. Judged by `docs/notes/ship_analysis_plan.md`, fixed before any run; predictions dated in the plan before any held-out ship run and scored by rules agreed before the report was opened. Reproduce: `uv run python scripts/ship_baseline_runs.py <B|C|B90>` and `... B --signs corrected`, then `uv run python scripts/ship_baseline_report.py` (report and per-run table in `results/ship_baseline/held_out/`, git-ignored).*

## What was run

20 held-out ship levels (easy 8, medium 8, hard 4) × seeds 0, 1, 2, whole brain, R_ship = 150 Hz, blind (D33), four batches:

| Batch | Encoding | Role |
|---|---|---|
| **B** | ω_self(vy − v_req), ω_full 30°/s, original signs | the design of record |
| C | ω_self(−v_req) | control: steering without the fly's stabiliser |
| B90 | B with ω_full 90°/s | labelled variant: the anchor's state |
| B, corrected signs | B on the T4/T5-corrected connectome (D27) | D28's sensitivity check |

**Checks (all passed, so everything was compared):** 60/60 runs per batch; every run replays exactly from its logged holds; settings as fixed; one clean commit (12a591f) for all 240 runs. Open-loop gate passed on both connectomes before their batches (0 DNp22 spikes with no input, 10/10 trials; `ship_open_loop.md`).

**Interruptions, none affecting the data:** a Windows update restarted the computer at 02:08 during B's seed 1, and joblib's worker pool broke twice (Windows `WinError 6`) during the corrected batch and the corrected open-loop checks. A run's files are written only when it ends, so each cut-off run left nothing; the missing runs were played again on the same commit, and every run passed the replay check. (Since then, `play_level.py` retries a broken pool by itself and resumes a killed batch.)

## Results

Median run per level:

| | Levels completed | Easy | Medium | Hard | Mean progress | Runs completed (of 60) |
|---|---|---|---|---|---|---|
| **B** | **6/20** | 5/8 | 1/8 | 0/4 | **45.6%** | 15 |
| B, corrected signs | 7/20 | 6/8 | 1/8 | 0/4 | 53.0% | 20 |
| B90 | 0/20 | 0/8 | 0/8 | 0/4 | 26.1% | 1 |
| C | 0/20 | 0/8 | 0/8 | 0/4 | 14.9% | 0 |
| B's ideal ship (no brain) | 14/20 | | | | 81.4% | |
| Never hold / always hold / random holds | 0/20 | | | | 6.7–8.5% | |

**Comparisons** (per level, median runs; D48's "equal"; two-sided sign test, "better"/"worse" only at p < 0.05):

| Comparison | Better | Worse | Equal | p | Reading |
|---|---|---|---|---|---|
| B against never hold | 20 | 0 | 0 | < 0.001 | better |
| B against always hold | 18 | 0 | 2 | < 0.001 | better |
| B against random holds (mean of 10 draws; all 10 draws: better) | 20 | 0 | 0 | < 0.001 | better |
| B against its ideal ship | 0 | 12 | 8 | < 0.001 | worse |
| **C against B** | 0 | 16 | 4 | < 0.001 | **worse: the stabiliser helps** |
| B90 against B | 0 | 10 | 10 | 0.002 | worse: the anchor's state matters |
| Corrected against B | 2 | 0 | 18 | 0.50 | no clear difference |
| C against random holds (mean of draws) | 12 | 8 | 0 | 0.50 | no clear difference |

- **Noise line:** no seed differs clearly from another in any batch (all p ≥ 0.07).
- **Stuck runs:** B 1, corrected 3, C 0, B90 0 (counted as played, D38).

## Deaths

Classified by the plan's procedure, in its order:

| Batch | (s) stuck | (a) unseen | (b) encoding's limit | (d↑) too high | (d↓) too low | (u) |
|---|---|---|---|---|---|---|
| **B** (45 deaths) | 1 | 0 | 5 | **39** | **0** | 0 |
| Corrected (40) | 1 | 0 | 4 | 35 | 0 | 0 |
| B90 (59) | 0 | 0 | 3 | 55 | 0 | 1 |
| C (60) | 0 | 0 | 6 | 53 | 1 | 0 |

**Spot-check of the classifier** (every (b), (d↑) and (d↓) death re-played, and the side of the killing block measured):

| Batch | (d↑) deaths | Ship hit the **underside** of a block above it | Ship hit a block **below** it |
|---|---|---|---|
| B | 39 | 36 | 3 |
| Corrected | 35 | 32 | 3 |
| B90 | 55 | 50 | 5 |
| C | 53 | 36 | 17 |

- In B, the ship was a median **72 units above** the ideal ship at death (range 14–192), and **falling** in 169 of all 182 (d↑) deaths across the batches: trying to come down, too late.
- **3 of B's 39 are borderline:** above the ideal path, but killed by a block below it. They are (d↑) by the plan's rule (height against the ideal ship); physically they hit a lower block.

## Why the fly errs high: the output rule plus the game's physics

| B's input | Ticks | Share of ticks released | Mean vertical speed (units/s) |
|---|---|---|---|
| "down", f > 0.5 | 39,693 | **67.5%** | **−35** |
| "down", 0.1–0.5 | 126,220 | 56% | +24 |
| "down", < 0.1 | 22,311 | 21% | +36 |
| "up" (any f) | 8,965 | 3–4% | +9 to +58 |

- In the game (`game/physics.py`), **holding while falling pushes up at 0.5 g, releasing while falling pulls down at only 0.32 g.** A falling ship speeds up its fall only if it releases on more than 0.5 / 0.82 ≈ **61%** of ticks.
- The rule releases on a tick if either DNp22 spiked in the frame before. Each DNp22 tops out near 110 Hz against the 240 Hz game clock (open loop: 114 Hz right, 94 Hz left at f = 1). So even at full "down" drive the fly releases on about two-thirds of ticks, **just past break-even**, and sinks at ~35 units/s against the ideal ship's 345.6.
- **So the fly climbs fast but descends slowly,** and reaches openings below it too high. B90 drives DNp22 more weakly (f is 3× smaller for the same motion), so it errs the same way, more.
- **This is the D53 output rule against the game's asymmetric gravity, not tuning.** DNp22 is already near its maximum at f = 0.25 (`ship_open_loop.md`), so a higher R_ship can't fix it. Any change to the output rule is a new decision, argued on its own merits.
- **For Stereo Madness:** its ship sections will be hardest wherever they need a fast drop. Stated before it runs.

## How it flies (described)

| | B | C | B90 | Corrected |
|---|---|---|---|---|
| Ship ticks held | 48.0% | 50.7% | 47.3% | 48.1% |
| Its ideal ship's | 47.7% | 51.6% | 47.7% | 47.7% |
| Switches per second (median hold, release: 1 tick each) | 142 | 108 | 145 | 138 |
| Lag, motion turns down → next release (median ticks) | 6 | 8 | 8 | 5 |
| Median \|vy − v_req\| (units/s) | 37.9 | 166.3 | 103.2 | 32.0 |
| Median \|error\| at each column passed (units) | 4.4 | 30.6 | 19.5 | 3.8 |

- **The ship alternates nearly every tick,** so its vertical speed is set by the share of ticks held. B tracks its target closely where it can: a median 4 units off the opening's centre at each column.
- **Which DNp22 releases (B):** of 102,598 release frames, right only 53,556, left only 28,110, both 20,932. The right drives more releases, as v783's weaker left side predicts; both at once is the minority.
- **DNp22 against the input (B):** ~37 / 99 / 113 Hz (right) for small / medium / large downward f, and ~5–7 Hz during "up" input (0 in open loop): probably carried over from the "down" drive just before.

## Predictions (Shannyn's, dated in the plan; scored by rules fixed before opening)

**8 hits, 2 misses** (1–2 not scored: the open-loop results existed before they were committed).

| # | Prediction | Result | Score |
|---|---|---|---|
| 3 | B beats never hold, always hold and random holds | better against all three | hit |
| 4 | B worse than its ideal ship; no hard level | 6 < 14 levels, 45.6% < 81.4%, 0/4 hard | hit |
| 5 | ≥ 4/8 easy, < 4/8 medium | 5/8, 1/8 | hit |
| 6 | Most deaths are (d) | 39 of 45 | hit |
| 7 | More (d↑) than (d↓) | 39 against 0 | hit |
| 8 | Held share above the ideal ship's | 48.0% against 47.7% | hit by the letter only: about equal |
| 9 | B better than C | C worse on 16, p < 0.001 | hit |
| 10 | B90 same or lower than B, with more (d↑) | worse; 55 against 39 | hit |
| 11 | Releases mostly from both DNp22s; one-sided more from the right | both 20%; right > left | miss |
| 12 | 0 stuck runs | 1 (known before opening) | miss |

**7's reason was close but incomplete:** silence = hold, *and* the game's asymmetric gravity, which together cap how fast the fly can descend.

## What this means

- **The fly flies the ship.** Driven by B's image motion, the whole brain's DNp22 output completes 6 of 20 held-out levels and beats every no-brain reference on every level.
- **The fly's stabiliser term matters:** without it (C), the brain does no better than random holds, although C's own ideal ship completes 9 levels.
- **The anchor matters** (B90 worse), and **the T4/T5 sign labelling doesn't** (corrected: no clear difference).
- **The main limit is the output rule against the game's physics:** too slow to descend, so every batch dies high.
- **Model limits to state** (D53): no gap junctions (VS–DNOVS coupling is electrical in the fly), no ocellar input, spiking VS cells, DNOVS cells encode rotation while the ship translates (our mapping), no behavioural state.
