# Step 7 proposal: the whole brain against the subcircuit, in closed loop

*Jacob, 2026-11-05. Draft for Shannyn (Step 7 is a shared step: she leads the comparison, Jacob the runs). No code, no new runs. **To fix before the Step 4 report is opened**, because the intact whole brain's results sit in that report: once we've read them, a comparison plan made afterwards could be shaped by them.*

**The question:** does the final subcircuit (D46: 33,486 neurons) play the cube like the whole brain (~139,000) on levels neither has seen? If it does, every subcircuit result (Steps 2–3, and Stereo Madness if run on it) stands for the whole brain. If it doesn't, we say where they part.

**Why it needs no new runs:** two batches already exist with **the same encoding, settings, levels and Poisson seeds**:
- the Step 2 baseline on the subcircuit (D48; `results/closed_loop/final/held_out/200deg_collision_R150[_seedN]`);
- the Step 4 intact whole brain (D51; `results/closed_loop/whole_brain/held_out/200deg_collision_R150[_seedN]_step4`).

Both are R = 150 Hz, R × f, θ_full = 200°, collision course, on the 20 held-out cube levels at seeds 0, 1 and 2: 60 runs each, all at clean commits (`5d9de12`; `91989c6`). I checked that every setting recorded in their `run.json` files matches. The only differences are the network and the stuck-state neuron list, which is restricted to each network (D38).

**The GPU (PROJECT_BRIEF's Step 7)** is deferred, as agreed (2026-11-05). The whole brain runs on the laptop, so this comparison doesn't need one.

## 1. The comparisons, fixed before reading

**(a) Identical games (primary).** Rule 5 (D46) found both networks pressing on the same frame on every judged approach when the bot drove. Fly-driven, the same holds if the two games are identical. Per level and seed (60 pairs), the question is whether the logged press sequences are identical tick for tick.
- **Bar (proposed): identical in at least 57 of 60 pairs (95%).** This is the same 95% as rule 5, applied to whole games, which is stricter.
- **For every pair that differs, described:** the first frame where the presses differ, what was in view (the approach, θ and the object), and whether it changed the outcome (the killing object, or completed).

**(b) Same outcome, per level (as Steps 3–4).** Each network's median run across the 3 seeds; D48's "equal"; the two-sided sign test. "No clear difference" is expected. With (a) near 100%, it's close to automatic, so it's reported, not the main bar.

**(c) Described:** mean progress, completions by difficulty, D48's death classes, first-spike θ with and without carry-over, stuck runs, presses per second, and run time per run (the subcircuit's speed advantage, for Step 6).

## 2. Readings, fixed now
- **(a) passes:** "In closed loop on unseen levels, the subcircuit plays exactly like the whole brain in N of 60 runs." Every subcircuit result stands for the whole brain, within this setting (cube, 150 Hz, D47's encoding).
- **(a) fails:** we report how many games split, where and why, and which results that touches.
  - **The subcircuit results stay valid as subcircuit results.** We don't rerun anything on the whole brain because of it, which would be choosing networks after seeing outcomes.
  - **Any later step (Stereo Madness, ship) runs on the network we fix before it starts,** knowing this result.
- **Scope:** this covers the cube at 150 Hz only. The 50 Hz variant (D50) and the ship need their own check if they run on the subcircuit. For the ship, that's the closed-loop check in `docs/notes/ship_brief.md` §5.

## 3. What it costs
- **Agreeing on this:** her review, about 15 minutes to log as D52.
- **Code:** done (2026-11-06), written blind: `scripts/step7_report.py` with `stereo_flyness/experiments/step7_analysis.py`. It reuses Step 2/3/4's tools (replay, classes, `paired`) and computes **both** candidate bars from question 1, so it works whichever one D52 fixes. Its dry run passed its checks (60 pairs, settings shared, all clean) and its output was deleted unread.
- **Runs:** none. **Report:** written blind, opened together right after the Step 4 opening, since it reads the same intact runs.

## 4. Questions for Shannyn
1. Is identical games ≥ 57 of 60 the right bar, or should it be per approach like rule 5 (first press within ±1 frame, ≥ 95% of approaches)? Per approach is more forgiving once games split, because later approaches no longer line up.
2. Should the 50 Hz variant get the same check before Stereo Madness (60 more whole-brain runs, ~1 night), or does Stereo Madness at 50 Hz run on the whole brain instead?
