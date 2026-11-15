# Iteration 2, fix 1: let the fly see the drop (option A)

*Jacob, 2026-11-15; **Shannyn's answers folded in the same day** (end). The design is agreed; her biology argument and predictions are still to come. **Nothing is run, not even step 2's ideal-fly check, until her predictions are in this note and D55 is logged.** The code (PR #62) exists, off by default.*

*Under the iteration-2 rules (`docs/notes/iteration2_proposal.md`, draft D55), each fix needs a dated design note with Shannyn's biology argument and predictions, written before it's run. This is fix 1's. Shannyn's sections are marked **[Shannyn]**. Nothing in it uses Stereo Madness beyond what the proposal already records.*

## The problem, in one paragraph

The encoding only shows the fly objects that overlap the cube's **current** height ("collision course", `interface/encoding.py`). Standing on a raised platform, the pits past its edge are below the cube, so they never loom: the fly gets no warning, walks off and falls in. In iteration 1, this was the second wall in Stereo Madness (33 of the 90 extra runs). Shannyn's framing (proposal, answer 2): looming already means "what you'll hit if you carry on", and adding gravity makes our collision course match that. **We don't claim flies use looming for gaps** (gap crossing is slow, parallax-based and driven by the central complex; option B, showing the edge, is future work).

## The change, in two parts

### Part 1: which objects are "on course" (the predicted path)

**Now:** an object is on course if it overlaps the cube's current vertical extent.

**Proposed:** an object is on course if it overlaps the cube's **no-press path**: where the cube would go if the fly never pressed again, under the game's exact physics (walking on, falling off edges, landing on solids). An object counts if the predicted cube overlaps the object's visual cell at any point while passing it.

- **Only while the cube is on the ground** (agreed). In the air, the current rule stays. This keeps the decision that **objects the cube lands onto are invisible** (agreed 2026-10-31: landing is a different behaviour from the escape, and a press in mid-air does nothing). Using the predicted path in the air would reverse that decision, which isn't part of this fix.
- **On the ground at floor level (y = 0) nothing changes.** The floor is solid everywhere (pits are hazards lying on it), so the no-press path is flat and covers exactly what the current rule covers. The only ticks that change are those with the cube **standing on something raised**: a platform, a block top, a slab, a stair step.
- **Plain edges stay silent.** Walking off a platform onto empty ground puts nothing on the path, so nothing looms. This is the `platform_step_down` control (levels note), true by construction, and checked anyway.

### Part 2: how big an on-course object looks (θ). This is the main question.

Computing θ honestly from where the eye is now **doesn't work**. From on top of a platform, the pit is below the eye, so its angular size stays small (pit visual cell 0–17 units, `angular_size` in `encoding.py`):

| Where the eye is | Largest θ the pit ever reaches |
|---|---|
| On the ground (eye at 15), as now | 177° (passes 39° at a gap of 22 units) |
| On a 1-block platform (eye at 45) | **13.5°** |
| On a 2-block platform (eye at 75) | **7.3°** |
| Falling, cube just touching the pit (eye at 32) | 21.2° |

The fly's threshold is ~39°, so with true optics the pits would loom **without ever triggering a jump.** That fits D44's finding that a spike seen from above reaches only ~11°. Three options:

| | θ of an on-course object | For | Against |
|---|---|---|---|
| **(i) True optics** | From the current eye, as now | No construction, honest geometry | Peaks at 7–14°: the fix changes almost nothing. Worth reporting as the reason (ii) is needed. |
| **(ii) Landing-level view** (agreed) | From an eye at the object's **base level** (its bottom + 15), as a cube standing at that level would see it, at the true horizontal distance. Only for objects on course solely because of the fall; objects already on course keep their usual θ. A pit past a platform's edge then looks as it would from the ground beside it. | Simple, no new dial. Matches "what you'll hit if you carry on": the warning arrives as if the cube were already down at that level. Equal to the current θ wherever the cube is on the ground at y = 0. | A construction, not optics. It has to be described as our encoding's choice, never as what the fly sees. |
| **(iii) Time to contact** | Replace θ with a looming signal derived from time to contact along the path | Closer to what looming really encodes | A new signal and a new calibration: much bigger than a fix to "in the way". Future work. |

**Agreed (Shannyn, 2026-11-15): (ii), framed like ship design B: our code supplies the foresight, the fly supplies the timing.** A falling fly does see a surface loom, but nothing in its eye predicts the fall, so (ii) is our construction. Her conditions:
- **(i) is reported alongside (ii)** in every check, so readers see what honest optics gives;
- **the replay labels it:** "θ shown from landing level, our construction" on every frame where it's used (the code flags these frames, `Loom.predicted`);
- **it's worded as our choice, never as what the fly sees.**

*(Wording note, 2026-11-15: the first draft said "the height the cube will land at". That isn't defined when the cube falls into a pit and dies, so the rule is the object's base level. For pits and anything standing on the floor the two are the same.)*

No new number is introduced: θ_full, the patch order, the rates and the 39° calibration all stay as they are. So fix 1 uses **none** of iteration 2's 2–3 dials.

**What (ii) does on a platform:**
- Pits right at the edge (k = 0–1 ground cells first) now loom at ground-level θ as the cube nears the edge. A fly that fires at ~39° jumps from the platform at the moment it would jump at a ground pit.
- Obstacles further past the edge (k ≥ 2) also loom earlier, from the platform rather than after landing. This could help (no short run-up after landing) or hurt (a jump from higher up flies further), and the ideal-fly check below measures which.
- A jump from 1–2 blocks up flies further than one from the ground, so wide pit strips may still not be cleared. That would be a limit of the jump, not of the warning.

## What doesn't change

- The connectome, the brain and the output rule (press while the Giant Fiber fires).
- θ_full, R, rate scaling, the patch order and the 39° calibration.
- Everything in iteration 1. The new behaviour sits behind an encoder option (e.g. `CubeEncoder(path="no_press")`), off by default, so iteration 1's code and results are untouched.
- Ship mode (nothing looms there yet).

## What it may not fix (for honesty up front)

The per-obstacle sweep (`scripts/ideal_fly.py --by-obstacle`, 50 cube training levels, 39°) found three walls:
- **Triple spikes** (0/10): a timing limit, not a visibility one. Fix 1 can't help.
- **Slab bridges and slab hops** (0/17): from the ground, the slab above isn't on the no-press path, so it still never looms. The fly reacts to the pits under it instead. (ii) only helps once the cube is **on** a slab, by warning it about the slab's far end. Getting **onto** a slab is a landing problem, **reported as a separate landing limit** (agreed), outside this fix.
- **Pits after a raised platform:** the case fix 1 is for. The v3 levels never have them, so the new `platform_drop` chunk (levels note) is needed to test it.

## How it's checked, in this order (fixed before anything runs)

1. **Code tests** (no fly):
   - with the option off, the encoding is identical to now on every tick of the bot's path through all iteration-1 training levels;
   - with it on, θ is identical on every tick where the cube is in the air or on the ground at y = 0;
   - a platform followed by pits makes the pits loom from the platform; a plain step-down makes nothing loom.
2. **Ideal-fly check (no brain), training levels only,** once the predictions are in and D55 is logged: `ideal_fly.py --by-obstacle` at 39°, current encoding vs (i) vs (ii). On the iteration-1 training levels and the iteration-2 training levels (frozen first). Reported per obstacle type, with `platform_drop` and `step_down_pits` split into **fix cases and controls** (per level: does a walk-off cube land in the pits?) and by pit width, plus `platform_step_down`.
   - **Gate (Shannyn, 2026-11-15):** if the ideal 39° fly with (ii) clears **fewer than 50% of the fix-case drops** on the iteration-2 training levels, we **stop before any fly runs** and report why.
     - **Refined 2026-11-15, before anything ran** (after Jacob's geometry check): one jump from a 1- or 2-block platform, taken at the 39° point, clears at most 3 pit cells (2 from the ground; scripted cube, game geometry, not a fly result). So the gate counts **only fix-case drops a single jump can clear (pit strips ≤ 3 cells)**. Wider strips are reported separately as a limit of the jump's geometry, so the gate tests the encoding, not the game's physics.
3. **Fly runs on the iteration-2 training levels** (whole brain, 150 Hz, the record settings). This is where the design can be revised, **at most once, logged with its reason** (rule d).
4. **Once, at the end of iteration 2:** the iteration-2 held-out suite (40 cube levels, opened once) and the iteration-1 held-out cube levels, with and without the fix.
5. **Then Stereo Madness** on fresh seeds (100 onwards, N fixed beforehand, agreed by both of us), reported only as how far the fly gets.

**Fix 1 counts** (rule c) if, on the iteration-2 held-out suite, the fixed fly does better than the unfixed one (paired test, p < 0.05), and on the iteration-1 held-out cube levels it is not clearly worse (no significant drop by the same test), with completed counts reported beside both. **No-harm condition (agreed):** at `platform_step_down` edges, the fixed fly jumps no more often than the unfixed one.

## [Shannyn] Biology argument

*Shannyn, 2026-11-15.*

**What looming is in the fly.** LPLC2 and LC4 respond to an object expanding on the eye, which signals an approaching collision; LPLC2 carries the object's angular size to the Giant Fiber and LC4 its angular velocity (Ache et al. 2019). A fly that is actually falling toward a surface does see it loom, so the moment the cube drops off the edge, the pits looming is ordinary optics.

**What no fly's eye does.** Nothing in the fly's visual system computes "if I keep walking, I'll fall off this edge and land in that pit". Before the fall, the pits are below the eye and stay small (true optics: 7–14° at most, option (i)), and real flies don't use the Giant Fiber escape to cross gaps: gap crossing in walking *Drosophila* is slow and deliberate, judged from parallax, and depends on the central complex (Pick & Strauss 2005; citation still to check).

**So (ii) is our construction, and is framed like ship design B:** **our code supplies the foresight, the fly supplies the timing.** The encoding predicts the collision the cube's current course leads to and shows it at the size it would have from the level the cube will land at. The brain still decides *when* to jump, at its own threshold, with nothing tuned: θ_full, the rates, the patch order and the 39° calibration are unchanged. This extends the meaning the encoding already has: an obstacle ahead on the ground only looms because the cube will keep moving forward into it; (ii) adds gravity to "keep moving".

**How the write-up words it:** "From on top of a platform, pits below the edge never loom with true optics (they peak at 7–14°, below the ~39° threshold). We therefore show on-course objects as they would look from the level the cube will land at. This is our encoding's prediction, not something the fly's eye computes; the fly's contribution is when it jumps." The replay labels it ("θ shown from landing level, our construction"), and (i) is reported alongside.

**What it doesn't claim:** that flies use looming to cross gaps, or that the Giant Fiber pathway anticipates falls.

## [Shannyn] Predictions (written before step 2 runs)

*Shannyn, 2026-11-15, before step 2 and before any iteration-2 level exists. Scored hit or miss when each step's results are opened; confidence is how sure I am, not part of the score.*

| | Prediction | Why | Confidence |
|---|---|---|---|
| Ideal 39° fly with (ii), fix-case drops: share cleared (gate: ≥ 50%) | **Passes the gate: ≥ 50% cleared.** Drops with the pits right at the edge are cleared more often than those set back from it | With (ii) the pits reach 39° at the same distance as from the ground (~22 units before the first pit), and a jump from 1–2 blocks up flies further than one from the ground, so most strips are cleared. When the pits are set back, that trigger point can come after the cube has left the edge, where it can't jump | Medium |
| Ideal 39° fly with (i), true optics: any change from now? | **No change** | The pits peak at 7–14°, never reaching 39° | High |
| Ideal 39° fly with (ii), control drops: better, same or worse than now? | **Same** | The trigger point (~22 units before the pits) comes after the cube has landed on the ground, where (ii) equals the current view | Medium-high |
| `platform_step_down` (no-harm): more edge jumps than the unfixed fly? | **No: zero extra** | Nothing is on the path past a plain edge, by construction | High |
| Slab bridges/hops: any change? | **No change in levels cleared** | Getting onto a slab is a landing problem, and (ii) only acts once on a slab | Medium |
| Iteration-1 training levels overall (ideal fly): better, same or worse? | **Same, within ±1 level** | v3 levels have no pits after platforms, so (ii) only changes rare raised-surface cases | Medium |
| Real fly, iteration-2 held-out: does fix 1 pass the bar? | **Yes** | Every level has a drop, and the ideal fly should clear most fix cases; the risk is runs dying earlier at other features, which makes ties | Medium-low |
| Real fly, Stereo Madness: furthest point reached (median of N) | **Median unchanged at ~9.2%**; the furthest run passes 10.9% | 7 of 10 record runs die at the double spike, before the pits, and fix 1 doesn't change the double spike. Only runs that get past it reach the pits | High for the median, medium for the furthest run |

**Dated corrections (2026-11-15, after Jacob's geometry check, before anything ran; no prediction changed):**
- **Prediction 1:** the reason overstated how far a platform jump goes. It clears at most 3 pit cells, so 4–5-cell strips can't be cleared by any single jump and the share has a ceiling below 100%. The prediction (≥ 50% of all fix-case drops) is kept and scored as written; the gate itself now counts only strips of ≤ 3 cells (above).
- **Prediction 3 (control drops):** the reason was wrong. The pits reach 39° while the walk-off cube is still in the air (it lands ~45 units out), not after it lands. The prediction ("same") still follows, because in the air (ii) uses the current rule, so both encodings agree.

## Shannyn's answers (2026-11-15)

1. **(ii) is defensible,** framed like ship B: our code supplies the foresight, the fly supplies the timing. Report (i) alongside, label it in the replay ("θ shown from landing level, our construction"), and word it as our choice, never as what the fly sees.
2. **Grounded ticks only:** agreed.
3. **Slabs:** reported as a separate landing limit.
4. **A gate:** if the ideal 39° fly with (ii) clears fewer than 50% of fix-case drops on training levels, stop before fly runs.
- **Process:** step 2 waits until her predictions are in this note and D55 is logged. One prediction she'll include: 7 of 10 record runs die at the double spike before the pits, so she expects **fix 1 alone to leave Stereo Madness's median at ~9.2%**.
