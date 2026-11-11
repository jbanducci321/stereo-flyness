# Ship encoding: options after the failed ideal-ship check (for discussion)

*Jacob, 2026-11-10. For Jacob and Shannyn's discussion. Nothing here is decided, and **no option has been tried**: per §1d, we agree the next candidate and its bar first, then run its ideal ship (about 30 s on the 50 training ship levels). Shannyn leads the ship design; this is the engineering side's summary.*

## What the check showed (`docs/notes/ship_ideal.md`)

- Neither ideal ship completed any training ship level; both die exactly where never hold does (the first obstacle near the floor, ~7% in).
- **Full geometry:** the forward-flight term pins it to the floor. Pooled over an empty area it's 0°/s midway but −136°/s at 30 units up and −290°/s at 15, so it always releases.
- **Self-motion only:** a working stabiliser. It holds whatever height it's at (48% held, hovering just above the floor), but nothing tells it where the openings are.

**The underlying problem, as I read it:** the draft rule *follows* the scene's motion (downward → release → descend). That's the right sign for the ship's own climb and fall (it counters them), but the wrong sign for the forward-flight term. Flying forward, edges below stream down and edges above stream up, so following that motion steers the ship **toward** surfaces, at any height. That holds for obstacle edges too, not just the floor and ceiling, so removing the floor and ceiling alone probably doesn't fix it. (A reasoning, not a result: it hasn't been run.)

## The options

| | Option | What the fly sees | What we could claim | Build | Main risk |
|---|---|---|---|---|---|
| **A** | **Narrow the motion encoding** | Shannyn's motion, with a stated change: e.g. drop floor and ceiling, limit the vertical field of view, or leave out the forward-flight term near the eye | Still a pure motion pathway | ~1 h | By the reasoning above, the flight term still pulls toward obstacle edges. Likely still fails |
| **B** | **Self-motion stabiliser plus a target height** | The self-motion term (as now), plus an error signal: our code finds the next opening's height and drives "down" when the ship is above it and "up" when below | Stabilisation is the fly's (VS cells' known role); **steering is our computed input**, stated as such, like the cube's looming signal | ~0.5 day | Close to "a relay plus a sign" for steering, so the claim is narrower. Most likely to fly |
| **C** | **Error signal only** (brief option b) | Only where the opening is, relative to the ship | Weakest: the motion pathway carries a position signal it doesn't carry in the fly | ~3–4 h | Same as B, without the biological stabiliser |
| **D** | **Optic-flow balancing** (bees centring in a corridor; PROJECT_BRIEF §3.2) | Compare motion above and below the horizon; drive toward the slower side | A known insect strategy | ~0.5–1 day | Needs the opposite sign to the draft's rule, which the VS → DNp22 pathway doesn't obviously support; biology framing is Shannyn's call |
| **E** | **Keep the draft and report the failure** | As drafted (full or self-motion) | An honest negative result: the motion pathway, as we can drive it, doesn't fly these levels | 0 | The ship sections of Stereo Madness are lost. Ship mode stays in either way (agreed 2026-11-05) |

## Questions for the discussion

1. **Which claim do we want for the ship?** A pure motion pathway (A, D, E), or "the fly stabilises, our code steers" (B), with the caveat stated as for the cube?
2. **If B or C:** how is "the next opening" defined (the nearest gap in the next obstacle column within 600 units? its centre height?), and how does its error map onto f (a scale like ω_full, fixed from geometry, not tuned)?
3. **The bar for the next ideal ship:** keep ≥ 50% of easy training levels, fixed before it runs?
4. **Order:** try one candidate, or agree two (say B and A) and run both ideal ships together, with the bar fixed for each first?
5. **Self-motion only stays as the control** in every case (Shannyn's §1d).

## What doesn't change

DNp22 as the readout (any spike releases, otherwise hold), R_ship as the one dial, the whole brain, both eyes with the asymmetry stated, and the 30°/s anchor wherever motion is encoded.
