# Stereo Madness: dated predictions

*Shannyn, 2026-11-13. **Written before any Stereo Madness run.** Committed before the runs start, and scored when the report is opened (D54), by the rules written here.*

**What they rest on:** only our own results. Of Stereo Madness we know its length (26,384 units, ~85 s) and nothing of its layout (D7, hard rule 5). No prediction uses what the real level looks like.
- **Cube, 150 Hz** (D48): 6 of 60 held-out runs completed, all easy; 29% mean progress; deaths mostly early jumps (d1).
- **Cube, 50 Hz** (D49): 23 of 60 completed, all easy; median progress +23.5 points over 150 Hz, though not significant (p = 0.118). Its early jumps turn into late ones.
- **Ship, B** (D53): 6 of 20 held-out levels completed, no hard level; every control death "too high", because the fly descends slowly.
- **Step 7** (D52): in the cube games, only a small set of neurons fires, and the games are identical tick for tick between networks.
- **The mixed-level results are unopened** and not used here.

## The predictions

| # | Prediction | Why | Scored as a hit if |
|---|---|---|---|
| 1 | **No variant completes Stereo Madness** | Completing ~85 s needs surviving every obstacle; the fly completes only easy held-out levels (cube 6/60 runs at 150 Hz, ship 0 hard), and never a hard one in either mode | 0 of 10 completed in all three variants |
| 2 | **The 50 Hz variant gets further than the record** | Its held-out median progress was 23.5 points higher, and it removes nearly all early jumps (d1), the record's main cause of death | 50 Hz median progress > the record's |
| 3 | **Corrected signs play exactly like the record in cube sections** | In cube mode we drive only LC4/LPLC2, and the correction changes only the T4/T5 neurons' outgoing synapse signs. If T4/T5 stay silent in cube mode, the two networks get the same input and behave the same | For every seed, the corrected run's game state (x, y, vy) is identical to the record run's on every tick up to the first ship portal (or to the end, if neither reaches one). Jacob checks this from the logs; it's a yes/no comparison |
| 4 | **Most record runs end in a cube section, not a ship section** | The cube fly is the weaker one. By the median run per level, it completes 2 of 8 easy held-out levels (`step2_report.md`), against the ship's 5 of 8 (D53) | At least 6 of the 10 record runs end in a cube section |
| 5 | **Any record run that dies in a ship section hits a block above it** (an upper block's underside) | All 39 of the ship baseline's control deaths were "too high": the fly climbs fast but descends slowly (D53) | Every record ship-section death is on an object above the ship's centre at death. Not scored if no record run dies in a ship section |
| 6 | **At least one stuck run across the 30** | Stereo Madness is long, and stuck runs became more common in longer plays (ship baseline: B 1, corrected 3 of 60 runs on ~31 s levels; bot-driven training mixed levels, played to the end: 11 of 50) | At least 1 stuck run in total |

**Scoring:** each prediction is a hit or a miss by the rule above, with no partial credit. A miss is reported as plainly as a hit. The headline stays the record's count and median whatever the predictions do (D50), and nothing here changes after the runs.

**Not predicted:**
- **The record's median progress as a number:** it depends on where the hard obstacles are, which we don't know.
- **Which section or object ends each run.**
- **How far into a ship section runs get.**
