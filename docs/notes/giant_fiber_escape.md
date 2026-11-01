# Giant Fiber escape: what the real fly does (von Reyn et al. 2014)

*Shannyn, task S3. Last updated 2026-10-30. Source: von Reyn CR, Breads P, Peek MY, Zheng GZ, Williamson WR, Yee ALY, Leonardo A, Card GM (2014). A spike-timing mechanism for action selection. *Nat Neurosci* 17:962–970.*

## Why this paper matters for us

Our cube jumps when the model's Giant Fiber (DNp01) spikes (D42), and its looming input is calibrated to this paper's angular threshold (D43). This note records what the paper found, what we took from it, and what it doesn't tell us.

## What the study did

- Presented projected looming stimuli (an expanding object mimicking an approaching predator) to freely standing flies, filmed at 6,000 frames per second (over 4,000 escapes). The looms covered size-to-speed ratios r/v = 8–140 ms.
- Silenced or activated the Giant Fibers genetically, to see which escapes need them.
- Recorded the Giant Fiber with whole-cell patch clamp in head-fixed flies watching looms.
- Filmed real damselfly attacks to compare the stimuli with a real predator.

## Findings

**1. Flies have two escape modes, and only the fast one needs the Giant Fiber.**
- The same loom produced either a **short** takeoff (~5 ms from wing raising to leaving the ground) or a **long** one (~13 ms). Long-mode flies raise their wings fully first, which gives a steadier takeoff.
- **Silencing** the Giant Fibers removed short-mode escapes but left long-mode ones. **Activating** them produced only short-mode escapes.
- So the Giant Fiber is necessary and sufficient for the short mode. Long escapes use other descending pathways.

**2. One Giant Fiber spike is enough, and a real loom causes only one or two.**
- In head-fixed recordings, looms caused **one or two Giant Fiber spikes per loom**, in 10 of 33 flies.
- Each spike was followed by leg extension (the jump) after ~0.9 ms and flight initiation after ~2.0 ms, matching known Giant Fiber → jump-muscle latencies. The paper cites earlier work that a single spike drives the jump and wing-depressor muscles.
- When the Giant Fiber was forced to fire a long train artificially, prolonged muscle contraction sometimes interfered with flight.
- In 9 of 33 flies, looms caused flight initiation without any Giant Fiber spike, which confirms a parallel non-Giant Fiber pathway.

**3. Looms on either side drive it.** The recorded Giant Fiber spiked to looms on its own side and on the opposite side. The text doesn't say whether opposite-side responses were weaker or rarer.

**4. Escapes trigger at a fixed angular size, after a fixed delay.**
- The timing of escapes fitted a model in which behaviour starts a fixed neural delay after the loom crosses an angular-size threshold. The threshold didn't change significantly with r/v.
- **Short-mode (Giant Fiber) escapes have a higher threshold but a shorter delay** than long-mode ones:

  | | Short mode (Giant Fiber) | Long mode | Giant Fiber silenced |
  |---|---|---|---|
  | Neural delay to takeoff | 30.1 ms | 45.7 ms | 44.5 ms |
  | Angular threshold (Fig. 5b, read off the plot) | **~39° (s.d. ~14°)** at r/v = 40 ms | ~30–32° | ~30–32° |

- The threshold values aren't in the text. We read them off Fig. 5b independently (Shannyn and Claude), to about ±1°. The exact fitted distributions are in their Supplementary Fig. 6, which we haven't seen.

**5. The fast mode helps against fast attacks.** For looms matched to the fastest damselfly attacks (r/v = 8 ms), 30% of short-mode escapes took off before the time of contact, against 6% of long-mode escapes and 0% with silenced Giant Fibers. At r/v = 40 ms there was no significant difference.

## What we took from it

| Finding | Where it's used |
|---|---|
| One spike drives a jump; real looms give one or two | D42: any Giant Fiber spike is a one-tick press, with no spike count or refractory window |
| Our model's Giant Fiber fires at 100–200 Hz while driven | D42 and D39: the rule takes the first spike; the README says the rates are unrealistic |
| Fixed angular threshold, independent of r/v | D41: the encoding is driven by angular size |
| Short-mode threshold ~39° (s.d. ~14°) | D43: θ_full is calibrated so the model's first Giant Fiber spike happens at 39° |
| Game looms: r/v = 48 ms for a single block, ~96 ms for a two-block wall | Inside the paper's tested range (8–140 ms), close to its 40 ms condition |
| Both-side responses | Consistent with the model's left Giant Fiber firing to right-side input (`docs/pathway_results.md`) |

## Limits for our project

- **"Giant Fiber spike = jump" models only the short-mode escape.** Real flies also escape through other pathways (long mode), which our cube doesn't have. This is caveat 3 in the PROJECT_BRIEF.
- **The calibration target is approximate:** it was read off a plot, it's a mean over a wide spread, and their threshold is the retinal size at a fixed delay *before takeoff*, which we treat as the size at which the Giant Fiber pathway triggers.
- **Head-fixed recordings** only showed Giant Fiber spikes in about a third of flies, so spike counts per loom come from a subset.
- **The paper doesn't identify the Giant Fiber's visual inputs.** LC4 and LPLC2 were shown as its looming inputs later (von Reyn et al. 2017; Ache et al. 2019), and their firing rates are the next reading (S3 question 2).

## Still open (S3)

- **LC4/LPLC2 firing rates during a loom,** to put the model's 25–200 Hz input range in context: von Reyn et al. 2017; Ache et al. 2019; Klapoetke et al. 2017.
- **Whether opposite-side looms drive the Giant Fiber more weakly** in real flies: possibly in this paper's Fig. 4 or Supplementary Fig. 5.
- **Where in the visual field LC4/LPLC2 synapses matter most:** Dombrovski et al. 2023, for a position-based patch order (D41's later refinement).
