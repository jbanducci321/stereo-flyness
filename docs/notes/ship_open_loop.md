# Ship open-loop checks before the baseline (D53)

*Jacob, 2026-11-10. The four checks in `docs/notes/ship_analysis_plan.md`, run before any held-out ship run: whole brain, original signs, D53's input (all T4d + T5d "down" or T4c + T5c "up", both eyes unless stated) at R_ship × f with R_ship = 150 Hz; 10 trials of 1 s each. Rates per cell, mean ± s.d. across trials. Reproduce with `uv run python scripts/ship_open_loop.py`; trials in `results/ship_open_loop/` (git-ignored).*

## Check 1, the gate: **PASS**

No ship input gave **0 DNp22 spikes in all 10 trials** (and 0 in DNp20 and the VS cells). The baseline may run.

## Checks 2–4 (described)

| Condition | f | DNp22 R | DNp22 L | DNp20 R | DNp20 L | VS R | VS L |
|---|---|---|---|---|---|---|---|
| "Down", both eyes | 0.25 | 100.8 ± 2.5 | 73.4 ± 2.0 | 88.6 | 36.3 | 137.7 | 100.6 |
| | 0.5 | 109.4 ± 2.3 | 88.6 ± 1.9 | 115.1 | 57.8 | 182.1 | 142.6 |
| | 1 | 113.8 ± 2.2 | 94.0 ± 1.2 | 133.3 | 71.8 | 226.6 | 185.9 |
| "Up", both eyes | 0.25, 0.5, 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| "Down", left eye only | 0.25 | 0 | 100.6 ± 1.8 | 0 | 40.1 | 0 | 104.1 |
| | 0.5 | 0 | 121.8 ± 2.5 | 0 | 59.0 | 0 | 144.3 |
| | 1 | 0 | 137.1 ± 2.4 | 0 | 73.0 | 0 | 187.3 |
| "Down" + "up" together, both eyes | 0.25 | 39.3 ± 3.6 | 27.3 ± 2.4 | 58.9 | 18.1 | 76.0 | 64.0 |
| | 0.5 | 79.0 ± 2.8 | 54.5 ± 1.7 | 97.9 | 44.7 | 138.4 | 111.4 |
| | 1 | 95.3 ± 1.6 | 80.2 ± 3.2 | 123.8 | 66.6 | 198.9 | 165.7 |

- **"Down" drives DNp22 on both sides; "up" alone drives nothing,** as in the pathway tests.
- **DNp22 is near its ceiling already at f = 0.25** (right: 101 Hz at 0.25, 114 at 1). Its rate carries little about *how fast* the scene moves above ~7.5°/s; the release rate will mostly say *whether* it moves down. Worth reading the baseline's input-output table against this.
- **The left eye alone drives the left DNp22 harder than both eyes together** (137 against 94 Hz at f = 1), as in the pathway tests: driving both eyes lowers DNp22 on each side.
- **"Up" at the same f as "down" roughly halves DNp22 at f = 0.25 and trims it at f = 1** (the S2-style suppression). D53 never drives both at once (one sign of the pooled motion), so this is context.
- Matches the smoke test with the brain in closed loop (2 training levels): DNp22 at ~46, 96 and 115 Hz on the right for small, medium and large downward f.
