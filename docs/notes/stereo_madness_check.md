# Stereo Madness timing check (Step 1)

*Shannyn, 2026-11-01. The PROJECT_BRIEF makes Shannyn the owner of the sealed Stereo Madness level: she checks the converted level's length and cube/ship section boundaries against a real playthrough. This note records that check. It contains timings only, no layout details (D7, D9).*

## What was compared

- **Our engine:** the search bot's winning run on the converted level (`uv run python scripts/bot_stereo_madness.py`, D21–D24). Its mode switches and finish time come from the run's events.
- **The real game:** a 100% playthrough video, *Geometry Dash - Stereo Madness 100% (All Coins)* (https://www.youtube.com/watch?v=_DNZw-5bcrc).
  - Shannyn compared the two by eye against the replay viewer.
  - Claude then timed the video frame by frame in a browser, reading frames directly from the video, as an independent check.
  - Shannyn also watched a no-coins playthrough (https://www.youtube.com/watch?v=Lwov0Pv7mPA) for comparison.

**Path differences don't matter.** The coin routes take different vertical paths (our level has no coins, D22), but the cube's forward speed is constant (311.58 units/s), so every portal is reached at the same time on any route.

## Results

The video starts **~0.48 s** before the cube moves (the cube enters the screen at ~0.45 s). Subtracting that offset:

| Moment | Video | Video − 0.48 s | Our engine | Difference |
|---|---|---|---|---|
| First ship portal (cube → ship) | ~26.00 s | 25.52 s | 25.52 s | ~0 |
| Cube portal (ship → cube) | ~40.63 s | 40.15 s | 40.15 s | ~0 |
| Second ship portal (cube → ship, final section) | ~73.90 s | 73.42 s | 73.43 s | ~0.01 s |
| "Level complete" | ~86.1 s | ~85.6 s | 84.57 s (finish) | ~+1 s, see below |

- **Precision:** about ±0.05 s per portal (frames stepped, not exact frame numbers); about ±0.3 s for the end, which is an animation rather than one event.
- **The gaps between portals don't depend on the offset:** 14.63 s and 33.27 s in the video, against 14.63 s and 33.28 s in our engine.

**Verdict: the three mode switches match the real game to within about one video frame.** That confirms the converted layout (where the portals are) and the forward speed (D20, D21).

## The end of the level

The video's "Level complete!" flash comes about **1 s after** our finish time. This is the game's ending animation, not a physics error:
- after the last structure, the camera eases to a stop (from ~84.9 s in the video the scenery barely moves);
- the ship is then pulled to the end, with the progress bar going 95% → 99% → 100%;
- only then does the flash play.

Our engine counts a run as finished when the cube reaches the level's end point (D22), which falls somewhere within that animation. **There are no obstacles after the last structure**, so this can't change whether a run survives the level. It only shifts the exact finish timestamp. It's recorded here as a definitional difference, and doesn't need fixing.

## Not checked here

- Individual obstacle positions: the bot beating the level (D24) is the evidence for those.
- The third ship portal, which D24 found unreachable, and the ship area of the final section: neither was looked at in the video.
