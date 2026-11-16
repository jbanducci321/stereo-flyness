# Iteration 2, fix 2: showing a spike group from its far end (considered and declined)

**Declined, 2026-11-16 (D58): nothing was built or run.** Shannyn's reasons are at the end. The proposal is kept as written, for the record.

*Jacob, 2026-11-16. A proposal for Shannyn. **It reopens D56's fix 2 decision ((a), a limit for now), so nothing is built or run until we both agree.** If we do, it follows fix 1's path: her argument and predictions first, then a no-brain check on the iteration-2 training levels with a gate fixed before it runs, then fly runs. Exploratory (D55). Nothing in it uses Stereo Madness beyond what D54 records (7 of 10 record runs died at its double spike).*

## Why look again

The step 3 runs (D57, read-only, training levels) show that **the real fly clears double spikes at the rate the spread model predicted**: 44 of 91 (48%) against 48–51%. Triple spikes: 0 of 28, as predicted. With fix 1 the fly now gets further, so the double spike is its top cause of death (15 → 32 deaths). It's a timing-spread problem, not a wrong threshold (`fix2_design.md`), and D56's options (b)–(d) all move the fly's threshold or output. This one changes only what the fly is shown, as fix 1 (ii) did.

## The proposal: (e) a group of touching spikes is one object, shown from its far end

- **Today** (collision course): each spike column is its own object. The fly's θ comes from the nearest one, so for a double spike it reacts to the first spike's front face.
- **(e):** spikes in touching columns on the same level are merged into one object. Its θ is computed from **the front face of its last spike** (the same size of face, just placed where the group ends). Single spikes are unchanged. So are blocks, pits and anything with a gap between spikes.
- **No number is chosen.** The far end is where the group ends, not a tuned offset, so (e) adds no D55 dial.
- **D45's approach rule** already treats one object as one approach, so a group is one approach.
- Replays flag the frames where it's used, with its own label (hard rule 10), e.g. *"spike group shown from its far end, our construction"* (wording for Shannyn).

**What it is, honestly:** our code supplies the foresight (where a group of spikes ends) and the fly supplies the timing, the framing D56 accepted for fix 1 (ii). It's a stronger intervention than (ii): (ii) shows real pits from a level the cube will really be on, while (e) moves where a hazard appears to start. It must be worded as our construction, never as what the fly sees.

## What the game geometry says (not a fly result)

Spikes in isolation after a full run-up, eye on the ground, θ = 2·atan(15/d); clear windows at the first spike from `fix2_design.md`'s geometry table; the fly's threshold drawn from its closed-loop spread, N(37.1°, 7.3°):

| Group | Cleared today | With (e) | Why |
|---|---|---|---|
| Double spike | 45% | **96%** | The jump moves one cell later: at 39° the first spike is at ~101°, inside its 38–178° window |
| Triple spike | 0% | 8% | Two cells later overshoots: the cube is already at the first spike |
| Spike, 1 cell, spike | 0% | 8% | Not merged (gap); stays as today, figure shown only for comparison |

(The 45% today matches the spread-aware ideal fly's 48% on whole levels, D56.)

**So (e) is a double-spike fix, not a triple-spike fix.** The triple spike's window (θ ≥ 97° at its first spike) is only ~13 units wide. The best fixed offset of any size would clear about half (53%, at a 36-unit offset), but that offset would be a number chosen for the result: tuning. **The triple spike stays a limit** of a one-shot reflex, as D56 says.

## What could go wrong (the check would show it)

- **Later landings.** A jump one cell later lands one cell later, maybe onto whatever follows.
- **Short run-ups** (e.g. landing just before a double spike): the far end may already be past 39°, so nothing changes there.
- **Groups on platforms, or after fix 1's drops**, and interaction with fix 1 (ii).
- **It may look like the answer key:** a critic could say we moved the trigger by exactly the extra width. The reply is that the rule is one geometric definition of "an object" for every spike group, set before any check, and the fly still decides when.

## The plan, if we agree

1. **Shannyn:** a biology argument (or a reason not to), the replay label, and predictions, all before anything runs.
2. **Code:** `CubeEncoder(..., groups="far_end")` beside fix 1's settings, default off, tested.
3. **The no-brain check**, on the iteration-2 training levels only: the spread-aware ideal fly (20 draws, as in D56) with and without (e), each with and without fix 1 (ii); by obstacle type and levels completed.
4. **A gate, fixed now:** (e) goes on to fly runs only if, with the spread-aware fly, (1) double spikes cleared rise by **at least 20 points**, (2) **no other obstacle type drops by more than 5 points**, and (3) levels completed rise by at least **N = 3** (D56's margin, noise 0).
5. **Fly runs** on the training levels, as fix 1's step 3; held-out and Stereo Madness only at the end, as D55 says.

## Questions for Shannyn

1. **Is (e) defensible enough to test?** Or does moving where a hazard appears to start cross the line that (ii) didn't?
2. **If it is:** does it replace D56's "(a) for now" for double spikes, with (b) left as it was?
3. **The gate above:** right thresholds?
4. **The label** for replays.

## [Shannyn] Declined (2026-11-16)

*Shannyn's answer to the proposal; Jacob agrees.*

**(e) isn't defensible as a fix.** Part 2 asks how far the fly gets once our interface stops limiting it, and fix 1 fit that: the pits were invisible because of our encoding. The double spike isn't like that: the encoding shows it correctly (the ideal 39° fly clears every one, D56), and the real fly fails because its timing varies, at exactly the rate the spread model predicted (48%, D57). (e) would make up for the fly's spread by moving where the hazard appears to start, which is our code aiming the jump. That is what fix 2's biology argument says the escape reflex doesn't do.

**So D56's "(a), a limit" stands.** The double spike is reported as a finding, now confirmed by the real fly; the triple spike stays a limit as before.
