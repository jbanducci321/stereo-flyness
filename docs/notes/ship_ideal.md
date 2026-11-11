# The two ideal ships (Step 5, Shannyn's §1d check)

*Jacob, 2026-11-10. The check in `docs/notes/ship_proposals.md` §1d, before the ship design is fixed: does Shannyn's motion encoding fly the levels at all? No brain. Settings agreed with Shannyn on 2026-11-10; the prediction below was written and committed **before any ideal ship ran**. Code: `stereo_flyness.interface.ship_encoding` (the encoding), `scripts/ideal_ship.py` (the runs).*

## What runs

- **Two ideal ships**, each using the draft encoding and output rule, with a fixed threshold in place of a brain:
  1. **Full geometry:** pooled image motion with both terms (the ship's own climb and fall, and forward flight).
  2. **Self-motion only:** the climb-and-fall term only, a pure stabiliser (brief option a).
- **The rule (sign only, Shannyn):** after each tick, if the pooled motion is downward (any amount), the next tick is **released**; otherwise **held**. That's the draft output rule with "a DNp22 spike" replaced by "downward motion", so silence (no motion) means hold.
- **The encoding (fixed, Shannyn 2026-11-10):** 37 directions, every 5° from −90° to +90°; each sees the nearest surface (visual cell, floor or ceiling) within 600 units ahead horizontally; directions that see nothing count as zero; the plain mean over all 37. ω_full doesn't matter here (only the sign is used).
- **Levels:** the 50 **training** ship levels (20 easy, 20 medium, 10 hard). Never held-out ones, never Stereo Madness.
- **Next to them:** never hold and always hold (`stereo_flyness.experiments.references`), on the same levels.

## The bar (fixed before the runs, Shannyn 2026-11-10)

A version **"flies the easy levels"** if it completes **≥ 50% of the easy training ship levels** (≥ 10 of 20). Medium and hard are reported too. Then §1d's table:

| Result | Then |
|---|---|
| Full geometry flies the easy levels | Adopt the full encoding |
| Only self-motion flies them | The forward-flight term is the problem: rethink before choosing |
| Neither flies them | The motion encoding can't fly these levels: discuss before any brain run |

Whatever is chosen, the self-motion ship stays as a control.

## Prediction, written before the runs (Jacob, 2026-11-10; shared with Shannyn the same day)

- **Full geometry: the ship is pulled to the nearer of floor and ceiling and stays there.** In an empty ship area (floor 0, ceiling 300, flying level), the pooled forward-flight term alone is 0°/s exactly midway, but −41°/s at 75 units up, −136°/s at 30 and −290°/s at 15 (sliding on the floor), and the same upward above the middle. Straight down and up always see the floor and ceiling, very close, so they dominate. With the sign-only rule, below the middle means release and above it means hold, so the middle is unstable. A ship level starts on the floor, so we expect it to **play much like never hold** and to die on the first obstacle at floor height.
- **Self-motion only: it holds roughly the height it's at,** switching between hold and release as its vertical speed changes sign. It doesn't see where the openings are, so it should clear only levels whose path stays near that height; we expect it to **also play close to never hold**, a little better at most.
- **So we expect neither to reach the bar.** Either way, the result is reported as it comes.

## Result (run 2026-11-10, after the prediction above was committed)

`uv run python scripts/ideal_ship.py`, 50 training ship levels, ~30 s. Full table in `results/ideal_ship/training.md` (git-ignored).

| Player | Easy | Medium | Hard | Mean progress | Held | On floor | At ceiling |
|---|---|---|---|---|---|---|---|
| Full geometry | 0/20 | 0/20 | 0/10 | 7.1% | 0% | 100% | 0% |
| Self-motion only | 0/20 | 0/20 | 0/10 | 7.1% | 48% | 10% | 0% |
| Never hold | 0/20 | 0/20 | 0/10 | 7.1% | 0% | 100% | 0% |
| Always hold | 0/20 | 0/20 | 0/10 | 6.7% | 100% | 0% | 59% |

*Held, on floor and at ceiling: mean share of ship-mode ticks.*

- **Neither ideal ship reaches the bar: 0 of 20 easy levels each.** No level of any difficulty was completed by either.
- **Both play exactly like never hold.** On all 50 levels, each dies at the same progress as never hold, on the first obstacle near the floor (36 blocks, 14 pits), about 7% in.
- **Full geometry, as predicted:** it starts on the floor, where the floor below streams downward, so it releases on every tick and slides along the floor (100% of ship ticks).
- **Self-motion only, as predicted:** it holds and releases about half the time each (48% held), hovering just above the floor, where it started. It never climbs away from it, since nothing in its input says where the opening is.
- **So §1d's third row applies: "the motion encoding can't fly these levels; we discuss before any brain run."** For Shannyn and Jacob to decide; nothing is changed here.

## Round 2: options B and C (Shannyn's §8, `docs/notes/ship_proposals.md` on sc-ship-settled)

*Written and committed **before** the round 2 runs (2026-11-10). The design is Shannyn's §8, agreed by Jacob; the bars are her §8d, copied here unchanged.*

**What runs** (sign-only ideal ships, as in round 1: downward ω releases the next tick, anything else holds), on the same 50 training ship levels:
- **B (candidate):** ω = ω_self(vy − v_req): the ship's own vertical motion relative to the motion that would reach the next opening.
- **C (control):** ω = ω_self(−v_req): steering only, no stabiliser.
- **Self-motion only (control):** ω = ω_self(vy), as in round 1.
- Never hold and always hold beside them.

Here ω_self(v) is the mean over the 37 directions of −v · d / (d² + Δy²), in °/s (empty directions count as 0); v_req = Δy · vx / dx, with Δy the target opening's centre minus the ship's y, dx the eye's distance to the column's front face (at least 30), clipped to +432 / −345.6 units/s; no target means v_req = 0. The next opening is §8a's: the nearest column the ship hasn't fully passed, within 600 units of the eye; its free stretches at least 30 tall; the one whose centre is nearest the ship's height (ties to the lower).

**The bars (§8d, fixed before the runs):**
- **B and C each:** ≥ 50% of easy training levels (≥ 10 of 20).
- **B also:** completes more training levels than self-motion only.
- If B fails its bar, we discuss before changing anything; nothing is tweaked and re-run unlogged. If B passes and C doesn't, B goes ahead and C stays as its control.

**A note on what this tests (Jacob, before the runs):** with the sign-only rule, B's decision reduces to "release when the ship rises faster than v_req" whenever some direction sees a surface ahead (always, in practice: the floor or ceiling). The geometry sets only the *size* of ω, which only the brain uses. So these ideal ships test the steering logic and the game physics, not how strongly the motion pathway would drive the fly.
