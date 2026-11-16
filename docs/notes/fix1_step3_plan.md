# Iteration 2, fix 1, step 3: the fly on the training levels (run plan)

*Jacob, 2026-11-15. A plan for Shannyn to agree **before anything runs**. Fix 1 passed its gate (D56), so step 3 of `docs/notes/fix1_design.md` comes next: the real fly, whole brain, on the iteration-2 training levels, with and without fix 1. Training levels only, so D55's extra-runs rule doesn't apply, but the scope, measure and reading are fixed here first, as for every step. Exploratory (D55).*

## What runs

| | |
|---|---|
| **Levels** | The 50 frozen iteration-2 training levels (20 easy, 20 medium, 10 hard; `configs/iteration2/level_suites.toml`) |
| **Arms** | **Unfixed** (today's collision course) and **fix 1 (ii)** (the landing-level view). (i) isn't flown: the gate check found it identical to the unfixed encoding on every drop (D56) |
| **Brain** | Whole brain, as fix 1's note fixes |
| **Settings** | The fly of record: θ_full 200° (D43/D45), R × f at R = 150 Hz (D50), original signs |
| **Seeds** | 0, 1, 2 for each arm |
| **Total** | 50 levels × 2 arms × 3 seeds = **300 runs** |
| **Commit** | One clean commit for all 300, stamped in each run (no tracked edits while they run) |
| **Output** | `results/iteration2/closed_loop/whole_brain/…`, separate folders per arm and seed (rule 7) |

**Time:** the whole brain runs ~16–26× slower than real time, but most runs end early (the ideal fly completed 4 of 50 with fix 1), so roughly **5–15 hours on 4 workers**. It runs in six batches (arm × seed), overnight, with `--resume` if a batch is interrupted.

**Commands** (one per batch; `LEVELS` is the 50 training level names):
```bash
uv run python scripts/play_level.py $LEVELS --iteration2 --network whole_brain --seed 0 --jobs 4 --quiet
uv run python scripts/play_level.py $LEVELS --iteration2 --network whole_brain --seed 0 --jobs 4 --quiet --fix1 ii
```
…and the same for seeds 1 and 2.

## The measure (D55), fixed before any run

- **The feature** of a level is its **first fix-case drop** (`platform_drop` or `step_down_pits` where a walk-off cube lands in the pits; `experiments/obstacles.py`). A level with no fix-case drop has no feature; it's left out of the main measure and counted.
- **A run gets past the feature** if the cube passes the drop's far edge alive. A run that dies before reaching it doesn't get past it.
- **A level gets past the feature** if at least 2 of its 3 seeds do (the median run).
- **Main measure:** levels where the fixed fly gets past the feature and the unfixed one doesn't, against the reverse; **sign test** over the levels that differ. On training levels this is **descriptive**: D55's bar is judged only on the held-out suite, at the end.

**Reported beside it:**
- per drop, all fix-case drops reached, by k (ground cells before the pits) and pit width: cleared share per arm;
- control drops: cleared share per arm (no harm expected);
- **no-harm at plain edges:** jumps taken while on a plain step-down, per arm (fix 1's bar: no more with the fix);
- progress (median per level), completions, deaths by obstacle type, stuck runs (counted, not re-run).

**Read only after all 300 runs have finished**, from one report written by a script fixed before the runs (`scripts/fix1_step3_report.py`, to be written and reviewed first).

## The one revision (D55 rule d)

If the fixed fly clearly fails where the ideal fly succeeded, the design may be revised **once**, logged with its reason, and the fixed arm re-run on the same levels and seeds. Both results are shown. The revision is decided by both of us after reading the report, and is logged before the re-run.

## What happens next

- **Whatever the result**, fix 1 goes on to step 4 only as D55 says: the held-out suites, opened once, at the end of iteration 2 (after fix 2 and fix 3 are settled), and judged by D55's bar.
- Shannyn's fix 1 predictions 7 (held-out) and 8 (Stereo Madness) stay unscored until then.

## Questions for Shannyn

1. **Whole brain, as the note says, or the subcircuit?** D52 found the subcircuit plays cube levels identically to the whole brain (60 of 60 games), and it's several times faster. Fix 1 changes only the input, through the same LC4/LPLC2 neurons. I'd keep the whole brain, as written, unless you'd rather have the speed.
2. **Is "the first fix-case drop" the right feature,** or should every fix-case drop the fly reaches count, each judged separately?
3. **Do you want to add predictions for step 3** (e.g. how many levels get past the feature with and without the fix) before it runs?
