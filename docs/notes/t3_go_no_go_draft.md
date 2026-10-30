# T3 go/no-go: draft for discussion

**Status:** draft by Jacob (with Claude), 2026-10-30. **Not agreed.** T3 is a joint decision. Once agreed, the verdict goes into `docs/FEASIBILITY.md` (Go / no-go, Status: complete) and `docs/decisions.md`. This note can then be deleted.

## The question

Can a frozen FlyWire v783 brain model, in its Shiu et al. form, plausibly play our game through its own escape and steering pathways, fast enough to tune on a laptop? If yes, Step 0 closes and T4 (the interface decisions) starts.

## Suggested verdict: GO, cube first

- **Cube (escape pathway):** GO.
- **Ship (steering pathway):** GO, but with more risk. Build it after cube, as planned (Step 5).

## Evidence

Every check below was judged by rules agreed before its results were seen.

| Check | Result | Where |
|---|---|---|
| Shiu et al. reproduced on v783 | Pass: MN9 67.7 Hz vs 67.0 Hz reference; ~400 active neurons | FEASIBILITY: Reproducing Shiu et al. |
| Frame-by-frame stepping matches the unstepped model | Pass: MN9 67.8 vs 67.7 Hz (t = 0.03); follows on/off input within ~1–2 frames | FEASIBILITY: Frame-by-frame stepping |
| Escape pathway (LC4/LPLC2 → Giant Fiber) | **GO**: 10/10 trials at every rate (77–205 Hz), first spike ~8–13 ms, controls give 0 | `docs/pathway_results.md` (D29) |
| Steering pathway (T4/T5 → VS → DNp20) | **GO**: "down" drives VS and DNp20 in 10/10 trials; "up" gives 0 and suppresses "down" by 88–100% | `docs/pathway_results.md` (D31) |
| Interim subcircuit reproduces the whole brain | **PASS** on all 7 held-out probes: verdicts identical, key rates within 7.1%, first spikes 360/360, 97–100% of active neurons kept | FEASIBILITY: Subcircuit (D36, D37) |
| Fast enough to tune | ~7.2 h for a 200-run grid on 30 s levels, inside the 10 h limit (D37) | FEASIBILITY: Subcircuit |
| Game ready (Step 1) | Engine, Stereo Madness conversion, bot, generators and replay viewer done (D20–D26) | PROJECT_BRIEF §7 |

## Step 0 tasks

| Task | Status |
|---|---|
| S1 setup, S2 target neurons, S4 test design, S5 subcircuit rule, S6 licence check | Done |
| S3 background reading | Notes in `docs/notes/` (only `dnovs.md` so far). Shannyn to confirm whether more are planned |
| J2 runner, J3 physics, J4 pathway tests, J5 subcircuit | Done |
| T1 PR reviews, T2 interpreting the pathway results | Done |
| **T3** | This note |
| T4 interface decisions | Next. Shannyn's cube draft is on `sc-interface-t4` |

## Risks carried into Step 2 (none blocks GO)

| Risk | What we know | What we'll do |
|---|---|---|
| **Stuck state** (`docs/cascades.md`) | ~0.2% per simulated second, the brain locks into a self-sustaining mushroom-body state. In a larger stuck state we could trigger, the right Giant Fiber still fires on a loom, but 40% weaker and ~25 ms later, and the left goes silent. The natural state's effect is untested | Flag and count stuck runs (D38); compare jump timing in stuck vs normal runs; the stuck-state share is the detector on the subcircuit |
| **Sustained Giant Fiber firing** | It fires continuously while driven, unlike a real escape (a few spikes) | The output rule (T4) turns spikes into one-tick presses |
| **Horizontal motion drives the ship pathway** | Horizontal T4/T5 drives DNp20 at ~60% of "down" | The ship input encoding must account for scrolling (T4, Step 5) |
| **Unbiological firing rates** | Direct Poisson drive gives rates far above real ones | Report it plainly; the dials are interface choices, not claims about the fly |
| **The subcircuit is validated on stand-in probes** | The real input encoding isn't fixed until T4 | Rebuild and revalidate the final subcircuit after T4 (D36) |
| **The cube may jump too early** | Shannyn's T4 draft predicts a ~17° threshold, ~320 ms before contact | That is what the untuned baseline (Step 2) is for; tune at most 2–3 dials (D5) |

## What would send us back

- The final subcircuit (after T4) fails the D36 tolerance even with D36's fallbacks (cut-off ≥ 20, a higher size limit).
- The untuned closed loop never produces a timed jump: for example, the Giant Fiber fires to every object or to none, whatever the dials.
- Stuck runs turn out to be common in game-length runs **and** to block jumping.

## To agree at T3

1. The verdict: GO, cube first, with ship as planned in Step 5.
2. The risks above are accepted and carried into Step 2.
3. Mark FEASIBILITY as complete and log the verdict as a decision (D39).
4. Start T4 from Shannyn's cube draft.
