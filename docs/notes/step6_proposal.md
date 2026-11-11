# Step 6: Stereo Madness runs, a proposal for discussion

*Jacob, 2026-11-10; Shannyn's answers added the same day (end). A draft to settle **before any Stereo Madness run**, after the Step 4/7 opening (16 Nov) and once the ship design is logged. Nothing here is decided. Built from the decision log only; of Stereo Madness itself, only its length was read (26,384 units, 84.7 s at normal speed), never its layout (D7, hard rule 5).*

## Already fixed (not up for discussion)

- **Run N times, not once** (agreed in principle 2026-11-02, Open list): N and the seeds fixed before any run; nothing changes between or after; **the headline is the full count and median progress, never the best run**; the replay shown is **picked by rule**.
- **150 Hz is the fly of record, the headline; 50 Hz runs beside it as a labelled variant, at the same N and seeds, always reported second** (D50).
- **The original connectome is the main version; the T4/T5-corrected version is always reported alongside it as a sensitivity check** (D28, for the ship and Stereo Madness).
- **Ship mode stays in whatever happens** (agreed 2026-11-05).
- Stereo Madness only runs through `scripts/play_level.py --stereo-madness-final`, alone and always blind (only progress and stuck flags printed).
- No tuning on it, ever (D7).

## To decide

### 1. The network

One run uses one network for the whole level, cube and ship sections alike. The ship runs on the **whole brain** (agreed 2026-11-10: the subcircuit was never checked on ship inputs).

**Proposal: the whole brain for every Stereo Madness run.** Step 7 says whether the subcircuit's cube results stand for the whole brain; either way, the whole brain is the fly itself, and it's the only network checked for both modes. A subcircuit run of Stereo Madness would need a new rule-5-style check for the ship, so it isn't proposed.

### 2. The variants

All at the same seeds. Changing one setting at a time from the record:

| Variant | R (cube) | Ship anchor | Connectome | Role |
|---|---|---|---|---|
| **Record** | 150 Hz | 30°/s | original | the headline |
| 50 Hz | 50 Hz | 30°/s | original | labelled variant (D50) |
| Corrected signs | 150 Hz | 30°/s | T4/T5-corrected | sensitivity check (D28) |
| Faster anchor | 150 Hz | 90°/s | original | labelled variant, **only if** the ship design adopts it (Shannyn's §4) |

*If the ship design changes the anchor or adds settings, this table follows the logged design. A full factorial (every combination) is 2 × 2 × 2 = 8 settings: not proposed, since each extra combination says little beyond its single changes.*

### 3. N and the seeds

**Proposal: N = 10, seeds 0–9, for every variant.**
- 10 gives a usable count and median ("k of 10, median X%") and a rough spread.
- **Run time** (whole brain, ~11.4 s of wall time per game second with 4 at once): a run that completes takes ~16 min; most runs end earlier. So 10 runs ≤ ~2.7 h per variant, and 3–4 variants ≤ ~8–11 h: **one night**.

### 4. The showcase replay (R4)

**Proposal: the record variant's run whose progress is closest to the median of its 10; ties go to the lowest seed.** Fixed before the runs, so the video shows a typical run, not a lucky one.
- The 50 Hz variant's replay is picked by the same rule, if shown, and labelled.
- **Optional, labelled:** the record variant's furthest run, captioned "the furthest of 10", never as the headline.

### 5. Order and blinding

1. Ship design logged; ship baseline and any tuning done (Step 5).
2. A mixed-level held-out check (cube and ship switching at portals) on the same settings, one night, blind (agreed: Shannyn, 2026-11-10).
3. This proposal fixed and logged as a decision.
4. All variants run in one batch, blind; no result is opened until all are done and the report's checks pass.
5. Opened the same way as Steps 4 and 7 (two independent reads, then compared).

### 6. What's reported

Per variant: completed (k of 10), median and spread of progress, where each run died (cube or ship section, and the object), stuck runs; the ship sections reached and passed; and, for context only, the bot's run (`scripts/bot_stereo_madness.py`).

## Shannyn's answers (2026-11-10)

All five proposals agreed by Shannyn; to log as a D entry with Jacob once the ship design is logged and before any Stereo Madness run.
1. **Whole brain** for every Stereo Madness run: yes.
2. **One change at a time from the record:** yes. The corrected-signs variant matters more for the ship than for the cube, because T4/T5 are the ship's input.
3. **N = 10, seeds 0–9:** yes.
4. **Showcase: the run closest to the median progress, ties to the lowest seed:** yes.
5. **Mixed levels first:** yes. It's the first time the brain switches modes at portals, and better to find a bug there than in the one Stereo Madness batch. So step 2 of §5 is no longer optional.
