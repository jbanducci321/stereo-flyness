# Step 4 and Step 7 opening: my verdicts

*Shannyn. Filled in alone on Sunday 15 Nov from 8 pm and **sent to Jacob by 11:59 pm Sunday**, before the Monday 16 Nov call (9–10). If Jacob's shared verdict sheet arrives first, copy these answers into it. Every bar below is copied from D51 and D52, fixed before any run. Fill in each section before reading the next part of the report. Don't commit this before Monday's discussion; afterwards it can be committed as the record of my independent read.*

Order: `docs/notes/step4_opening.md`. Report: `results/step4/report.md`, then the Step 7 report.

---

## Step 4: controls and lesions (D51)

### 1. Checks: stop here if any fail

| Check | Expected | Report says | OK? |
|---|---|---|---|
| All 11 conditions at 60 runs | yes | | |
| Clean commits | yes | | |
| Every connectivity file matches its SHA-256 | yes | | |
| Stuck runs | 0 | | |
| Unclassified deaths (u) | 0 | | |
| LC4/LPLC2 silenced: 0 Giant Fiber spikes, 0 presses | yes | | |

All pass? ☐ yes ☐ no → if no, stop: nothing is compared.

### 2. The intact whole brain (the reference)

| | Step 2 subcircuit (D48) | Intact whole brain |
|---|---|---|
| Mean progress | 29% | |
| Runs completed | 6 / 60 (all easy) | |
| (d1) deaths | 33 | |
| First-spike θ without carry-over | 37.1 ± 7.3° | |

First impression (one line):

### 3. (a) and (d): does play depend on the wiring?

**Bar:** "depends on the wiring" if worse than intact at p < 0.05 (sign test over levels).
**Prediction:** worse than intact, playing like never press (6.3%), or always press if they run away.

| | better / worse / equal | p | Bar met? | Plays like |
|---|---|---|---|---|
| (a) degree-preserving shuffle | | | | |
| (d) random network | | | | |

### 4. (b) and (c): is it a relay?

**"It's a relay" only if all three pass:**
1. progress: no clear difference from intact;
2. pooled median first-spike θ (no carry-over) within the largest intact seed-to-seed difference (a Giant Fiber that never fires fails);
3. (d1) share within the same kind of range (no deaths = share of 0).

If 1 passes but 2 or 3 fails: "plays about as far, but not the same way". **If either does better than intact, it's the late-threshold effect, not "a relay plays better".**

| | 1. Progress | 2. θ | 3. (d1) share | Verdict |
|---|---|---|---|---|
| Intact seed range (for 2 and 3) | — | | | — |
| (b) looming-kept shuffle | | | | |
| (c) relay only | | | | |

**My prediction for (b):** earlier jumps, more (d1), progress the same or lower. **Dated note:** open loop it fired later (46.6° vs. 38.0°), so the "earlier" part is expected to miss.

(b): ☐ hit ☐ miss ☐ partial. Why:

### 5. E5b and E5c: is it those neurons?

**Bar:** differs from intact **and** from its recruited-matched control at p < 0.05, **in the same direction**.

| | vs. intact (direction, p) | vs. recruited-matched control (direction, p) | Specific? |
|---|---|---|---|
| E5b (22 inhibitory) | | | |
| E5c (12 excitatory) | | | |

**My predictions:**

| | Prediction | Result | Hit? |
|---|---|---|---|
| E5b first spike | earlier (below ~37°); open loop 35.0° | | |
| E5b (d1) | more | | |
| E5b progress | lower | | |
| E5c first spike | later; open loop 106.7° | | |
| E5c (d1) | fewer | | |
| E5c (d2) | more | | |
| E5c progress | same or higher (**if higher: late-threshold effect, not an improvement**) | | |

### 6. The lesion controls

**Prediction:** no clear difference from intact.

| | vs. intact (direction, p) | As predicted? |
|---|---|---|
| Old random-lesion control, E5b | | |
| Old random-lesion control, E5c | | |
| Recruited-matched control, E5b | | |
| Recruited-matched control, E5c | | |

### 7. Holm (family of 12)

| Test | Raw p | Survives Holm? |
|---|---|---|
| (a) vs. intact | | |
| (b) vs. intact | | |
| (c) vs. intact | | |
| (d) vs. intact | | |
| E5b vs. intact | | |
| E5c vs. intact | | |
| Old control E5b vs. intact | | |
| Old control E5c vs. intact | | |
| Recruited-matched E5b vs. intact | | |
| Recruited-matched E5c vs. intact | | |
| E5b vs. its recruited-matched control | | |
| E5c vs. its recruited-matched control | | |

### 8. Predictions: one line each

- (a), (d):
- (b):
- (c): no prediction. What happened:
- E5b:
- E5c:
- Random lesions:

### 9. Only now: anything else (labelled as interpretation)

- What surprised me:
- Worth a sentence in the write-up:
- Questions for Jacob:

---

## Step 7: whole brain vs. subcircuit (D52)

### Checks

| Check | Expected | Report says | OK? |
|---|---|---|---|
| 60 pairs at each rate | yes | | |
| Commits as listed (150 Hz: `5d9de12` vs `91989c6`; 50 Hz: `61a9bf6` vs `03eff81`) | yes | | |
| Settings match within each pair | yes | | |

### The bar: identical games in ≥ 57 of 60 pairs, per rate

Identical = the cube's (x, y, vy) is exactly the same on every tick, and the same number of ticks.

| Rate | Identical pairs | ≥ 57? | Reading |
|---|---|---|---|
| 150 Hz (fly of record) | / 60 | | |
| 50 Hz (labelled variant) | / 60 | | |

**Fixed readings:** a pass means the subcircuit's results stand for the whole brain at that rate (cube, D47 encoding). A fail means they stay valid as subcircuit results, nothing is rerun, and later steps run on the network fixed before they start.

### Splits (for each pair that differs)

| Level / seed | First differing tick | What was in view | Which network pressed | Outcome changed? |
|---|---|---|---|---|
| | | | | |

### Described only

- Per-approach agreement up to the first split:
- Per-level sign test:
- Anything notable (progress, completions, death classes, θ):

### My summary for Monday (2–3 lines)
