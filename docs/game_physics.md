# Game physics reference (Geometry Dash 2.2, cube + ship)

**Purpose:** the facts our own Python game engine must reproduce so that our levels, including the Stereo Madness recreation, play like the real game. Gameplay must be exact; visuals don't (D20).

**Rules followed:**
- **Facts only.** Numbers and rules were read from the sources below. No code was copied; our engine is written from this document.
- Each fact lists its source and a confidence level:
  - **High:** read directly from the decompiled 2.2 code, or confirmed by two sources.
  - **Medium:** one source, or derived.
  - **Low:** inferred or unverified.

## Sources

| Source | What it is | License | Used for |
|---|---|---|---|
| [camila314/gdp](https://github.com/camila314/gdp), branch `2.2`, commit `43e2c36` (2025-09-23) | Decompiled GD 2.2 physics functions | **None** (read only) | Tick loop, jump/ship physics, collision rules, stair snapping |
| [Open-GD/OpenGD](https://github.com/Open-GD/OpenGD), commit `2a0e307` (2025-07-31) | Open-source reimplementation of GD (2.1-era) | GPL-3.0 (read only; no code copied) | Per-object hitboxes, player hitbox size, position update, ground/ship bounds, object types |
| Community wiki/guides | Fan documentation | (facts only) | Ship bounds of 10 blocks; cube jump height ≈ 2.13 blocks |
| Jacob's screen recording (2026-10-22) | 49 s practice-mode run of Stereo Madness on the GD 2.2 mobile app, with **Show Hitboxes on** (~59 fps, 1564 × 720). Local only, not committed. | Our own measurement | Independent check of jump arc, timing, hitboxes and ship area (§9) |

Abbreviations: *gdp* = camila314/gdp; *OpenGD* = Open-GD/OpenGD. Function names refer to those repos.

## 1. Units, coordinates and time

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Block size | **30 units** | gdp `checkSnapJumpToObject` (`blockLength = 30`), OpenGD hitboxes | High |
| Physics tick rate | **240 ticks per second** (`stepCount = delta * 240`) | gdp `GJBaseGameLayer::update` | High |
| Time unit for velocities | Velocities are in **units per 1/60 s** ("per frame at 60 fps"). Each tick passes `dt = 0.25` of these frames to the player update. | gdp `GJBaseGameLayer::update` (`physicsSecond = delta*60/stepCount`) | High |
| Vertical time scaling | The player update scales vertical time by **0.9**: gravity and jump logic run with `dt_y = 0.9 * dt = 0.225`, and `y += vy * dt_y` | OpenGD `PlayerObject::update`; confirmed by stair-snap spacings (§6) and video timing (§9) | High |
| World y of the ground surface | **90**: a cube resting on the ground has its centre at y = 105 | OpenGD `checkCollisions` | Medium (the offset to level-file coordinates is checked in checkpoint 2) |
| Upper kill limit | y > 1290 → death | OpenGD `checkCollisions` | Medium (irrelevant to Stereo Madness) |

**Speed (normal, "1×"; Stereo Madness never changes speed):**

| Fact | Value | Source | Confidence |
|---|---|---|---|
| `playerSpeed` | 0.9 | gdp `updateTimeMod` (normal-speed branch) | High |
| `speedMultiplier` | 5.77000189 | gdp `updateTimeMod` | High |
| Horizontal speed | `x += dt * speedMultiplier * playerSpeed` = **1.29825 units per tick = 311.58 units/s = 10.386 blocks/s** | gdp constants + OpenGD update | High |

## 2. Per-tick update order

From gdp `GJBaseGameLayer::update`, each tick runs in this order:
1. **Player update:** jump/ship logic changes the vertical velocity, then the position moves by the new velocity. This is semi-implicit Euler: velocity first, then position.
2. **Collision checks:** solids, hazards, portals and the ground/ceiling, which may snap the position and kill the player.
3. Rotation (cosmetic), camera, triggers.

We use 64-bit floats with this same order (D20). Bit-exact float32 matching isn't attempted.

## 3. Cube

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Jump velocity | **+11.1800318** units per frame | gdp `updateTimeMod` (`m_yStart`, normal speed) | High |
| Gravity | **0.958199024** per frame², applied as `vy -= gravity * dt_y` each tick | gdp `updateTimeMod` (`m_gravity`) + `updateJump` | High |
| Max fall speed | vy is clamped to ≥ **−15** while falling | gdp `updateJump` | High |
| When a jump happens | Every tick where the cube is **on the ground and the button is held**. Holding therefore re-jumps the instant it lands. | gdp `updateJump` (`m_isOnGround && m_jumpBuffered`) | High (whether `m_jumpBuffered` means exactly "held" is medium) |
| No ceiling in cube mode | Only the ground (y = 90) | OpenGD `checkCollisions` | Medium |

**Derived numbers** (simulated from the constants above, 240 Hz with the 0.9 vertical scaling):

| Quantity | Value |
|---|---|
| Jump peak | 63.97 units = **2.13 blocks** (community figure: 2.13 ✓) |
| Airtime, flat ground | 103 ticks = 0.429 s |
| Jump length, flat ground | 133.7 units = **4.46 blocks** |

## 4. Ship

Values are for normal size and normal gravity, as in Stereo Madness. Velocities are in units per frame; `dt_y = 0.225` per tick.

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Base gravity | 0.9582 (fixed for flying modes) | gdp `updateJump` | High |
| **Holding:** upward acceleration | `vy += 0.9582 * dt_y * k`, with **k = 0.5 while falling, 0.4 while rising** | gdp `updateJump` (ship branch) | High (the exact meaning of "falling" is medium, §8) |
| **Released:** downward acceleration | `vy -= 0.9582 * dt_y * 0.4 * m`, with **m = 1.2 while rising, 0.8 while falling** | gdp `updateJump` | High |
| Speed limits | **−6.4 ≤ vy ≤ +8.0** | gdp `updateJump` (clamps 8.0 and 0.8 × −8) | High |
| Floor/ceiling contact | Position snaps to the boundary and vy is set to 0. **No death**: the ship slides along floor and ceiling. | OpenGD `checkCollisions` | Medium |
| Play area | **10 blocks (300 units)** between floor and ceiling | Community wiki + OpenGD | High |
| Area placement | On entering a ship portal: centre = 240 if portal y < 270, otherwise `floor(portalY/30)*30`. Floor = centre − 150, ceiling = centre + 150. For a low portal, the floor is the ground (90) and the ceiling is 390. | OpenGD `PlayLayer` (portal activation + bounds) | Medium (2.1-era; checked against the level in checkpoint 3) |

**Derived numbers** (from rest / from limits):

| Quantity | Value |
|---|---|
| Hold from vy = 0 to +8 | 93 ticks = 0.39 s |
| Release from +8 to −6.4 | 170 ticks = 0.71 s |

## 5. Collisions, hitboxes and death

**Player hitboxes** (OpenGD player texture rect; gdp `getObjectRect(0.3, 0.3)`):

| Hitbox | Size | Used for | Confidence |
|---|---|---|---|
| Outer | **30 × 30 units**, centred on the player | Hazards, portals, landing | High |
| Inner | **30% of outer = 9 × 9 units**, centred | Death from **solid blocks** | High |

**Solid blocks** (gdp `collidedWithObjectInternal`):
- **Landing:** when overlapping a block, if the player's bottom is at most **10 units below** the block's top (**6** for the ship), the player snaps onto the top. It's then on the ground; for a cube, a held button jumps on the next tick. (High)
- **Ship hitting a block's underside:** snaps below it (a "head bump") without dying. (High)
- **Otherwise** (e.g. running into a block's side, or a cube hitting an underside): the player dies **only if the block overlaps the 9 × 9 inner hitbox**. (High)

**Hazards** (spikes, pits): the player dies if a hazard's hitbox **overlaps the 30 × 30 outer hitbox**. (Medium-high, OpenGD `checkCollisions`; consistent with gdp's damage path.)

**Portals:** activate when the outer hitbox overlaps the portal's hitbox. Each portal triggers once.

**Object hitboxes** (OpenGD `_pHitboxes`, centred on the object's centre; width × height in units):

| Object ID | What | Type | Hitbox (w × h) | Confidence |
|---|---|---|---|---|
| 1–4, 6, 7, 62–83 (most), 90–96, … | Standard blocks | Solid | 30 × 30 | High |
| 40 | Slab / plank | Solid | 30 × 14 | Medium. **The video suggests the slab's top sits flush with the top of its grid cell, not centred as in OpenGD.** Resolve with level data (checkpoint 2). |
| **8** | Spike | Hazard | **6 × 12**, centred | **High: video measured ≈ 6.5 × 12.5 (including the drawn outline), centred on the spike** |
| 39 | Half spike | Hazard | 6 × 5.6 | Medium: vertical offset unverified |
| 103 | Small spike | Hazard | 4 × 7.6 | Medium |
| 9, 61 | Ground "pit" spikes | Hazard | 9 × 10.8, 9 × 7.2 | **9: High: video measured ≈ 9 × 10.7, straddling the ground line, one per block.** 61: Medium. |
| 12 | Cube portal | Portal | 34 × 86 | Medium |
| 13 | Ship portal | Portal | 34 × 86 | **High: video measured ≈ 34 × 84** |

The object types come from OpenGD `object.json`: 0 = solid, 2 = hazard, 5 = ship portal, 6 = cube portal, 7 = decoration. The full ID mapping for Stereo Madness is built in checkpoint 2, from the objects that actually appear.

## 6. Stair snapping (cube)

When a cube lands on a block after landing on another block, gdp `checkSnapJumpToObject` checks the offset between them. At normal speed, if the new block is (±1 unit):
- **120 units ahead and 1 block higher**,
- **150 units ahead and 1 block lower**, or
- **90 units ahead and 2 blocks higher**,

then the cube's x is nudged (by at most 1 unit per landing) to keep its distance from the block the same as on the previous one. This keeps held-jump staircases consistent. (High)

**These spacings also confirm the 0.9 vertical scaling.** Simulating a held jump onto the next step, compared with the spacing (units):

| Step | With 0.9 scaling | Without | Snap spacing |
|---|---|---|---|
| +1 block | 115.5 | 103.9 | 120 |
| +2 blocks | 84.4 | 75.3 | 90 |
| −1 block | 148.0 | 133.7 | 150 |

Only the 0.9 version is close enough for a 1-unit nudge to be meaningful.

## 7. Not modelled

- **Cosmetic:** cube rotation, particles, camera shake and movement, colours, background.
- **Not in Stereo Madness (D6):** orbs, pads, gravity flips, mini size, slopes, speed changes, dual, other game modes, platformer mode.
- **Audio:** the song and sound effects are replay features (D19), loaded from the user's local files, never committed.

## 8. Open questions (resolve by validation, not assumption)

| Question | Current assumption | How we'll check |
|---|---|---|
| Exact meaning of gdp's `playerIsFallingBugged()` (selects the ship 0.5/0.4 and 0.8/1.2 factors) | Falling ⇔ vy < 0 (normal gravity) | Ship arcs vs gameplay video; the bot beating the ship sections |
| Does `m_jumpBuffered` mean "button currently held"? Are presses buffered in mid-air? | Held = buffered; no mid-air buffer for the cube | Bot + video; relevant to the brain readout rule (T4) |
| ~~Vertical offsets of the half-spike (39) and slab (40) hitboxes~~ | **Resolved (§10):** hitboxes are centred on the object's *position*, and the level places these objects off-centre in their cell (slab at cell centre + 8, so its top is flush with the cell top, as in the video) | — |
| Ship area placement rule in 2.2 | OpenGD's 2.1-era rule (§4). The first ship section fits it (ceiling pits at level y 297 under a ceiling at 300). | All 3 ship portals checked in checkpoint 3 |
| ~~Level-file y coordinates vs world y~~ | **Resolved (§10):** world y = level y + 90 | — |
| Collision order within a tick for multiple overlapping objects | Process in order of x | Bot validation |

## 9. Video validation (2026-10-22)

**The recording:** Jacob's 49 s practice-mode run of Stereo Madness (GD 2.2, mobile, **Show Hitboxes on**).
- Practice mode draws the player's hitbox every tick as an axis-aligned yellow square, outlines hazard hitboxes in red, and outlines portals in green. So the trail traces the hitbox exactly in world space.
- **Analysis:** frame-by-frame pixel measurement using the frame timestamps. The scripts were scratch analysis, not committed.
- **Scale:** **2.25 px per game unit**, from the camera's scroll speed (≈ 701 px/s = 311.58 units/s). This is consistent with the 30-unit player box measuring 66–67 px.

| Check | Measured | Predicted (this doc) | Verdict |
|---|---|---|---|
| Cube jump peak (ground to apex) | 144 px = **64.0 units** | 63.97 units | ✅ |
| Time from takeoff to apex | **≈ 0.22 s** (two clean jumps; fitted gravity ≈ 2,550 units/s²) | **0.216 s with the 0.9 scaling**; 0.194 s without | ✅ Supports the 0.9 scaling. Without it, the error would be ~13%. |
| Horizontal speed | ≈ 701 px/s | 311.58 units/s | ✅ Consistent (it also sets the scale) |
| Spike (8) hitbox | ≈ 6.5 × 12.5 units, centred | 6 × 12, centred | ✅ (the drawn outline adds about a pixel per side) |
| Ground pit (9) hitbox | ≈ 9 × 10.7 units, straddling the ground, 1 per block | 9 × 10.8 | ✅ |
| Ship portal hitbox | ≈ 34 × 84 units | 34 × 86 | ✅ |
| Ship play area (floor to ceiling) | ≈ 672 px ≈ **299 units** | 300 units (10 blocks) | ✅ |
| Ship hitbox | ≈ 30 × 30 units (visual) | Not specified before | ✅ Same as the cube |
| Slab (40) vertical placement | Top surface flush with the top of a grid cell | OpenGD centres it | ⚠️ Possible mismatch; check level data |

**Not measurable from this video:**
- the ship's vertical accelerations (we don't know when the button was held);
- where the ship area sits relative to the portal (the camera moves at the transition);
- the half-spike hitbox (none was seen close up).

Those are left to the level data (checkpoint 2–3) and the bot (Step 1).

## 10. Stereo Madness level data (checkpoint 2, 2026-10-23)

### Source
- **Official layout:** the main-level data in Open-GD/OpenGD `Content/Custom/mainLevels.json` (commit `2a0e307`, SHA-256 pinned), key `"1"`.
  - It's RobTop's level data, not OpenGD code. It's downloaded locally by `scripts/fetch_stereo_madness.py` and never committed (D9).
- **Decoding:** main-level strings are stored without the standard gzip header (`H4sIAAAAAAAAA`). With it restored, they decode with Python's standard library (base64 + gzip). **No new dependency.**
- **Cross-check:** the archived server copy, level **77236587** ("Stereo Madness", GD 2.1 upload).
  - **All 1,399 gameplay objects are identical.** The only differences are 3 secret coins stored under different IDs (142 vs 1329).
  - Level **94729537** ("stereo madness copy") is **not** Stereo Madness: its first spike is at x = 20,295, and it uses gravity portals. **Rejected.**

### Format
- **Level string:** `settings;object;object;…`.
- **Each object:** `key,value,key,value,…`. Keys used in Stereo Madness:

| Key | Meaning |
|---|---|
| 1 | Object ID |
| 2 | x |
| 3 | y |
| 4 | Flip x |
| 5 | Flip y |
| 6 | Rotation (degrees) |
| 7–13 | Trigger and coin settings (not gameplay) |

### Coordinates

| Fact | Value | Confidence |
|---|---|---|
| Position meaning | Object positions (keys 2, 3) are the object's **centre**, in level units | High |
| Ground in level coordinates | y = 0 (objects resting on it sit at y = 15) | High |
| Level to world | **world y = level y + 90** (§1: ground surface at world y 90) | High |
| Hitboxes | Centred on the object's position (§5). Objects that sit low or high in their cell have that offset built into their y. | High |
| Examples | Spike: y = 15. Half spike (39): y = 6. Ground pit (9): y = 2, so its hitbox straddles the ground (matches the video). Slab (40): y = 23/53/83 = cell centre + 8, so a 14-unit hitbox has its top flush with the cell top (matches the video). | High |

### Inventory (2,291 objects)

| Category | IDs (count) | Total |
|---|---|---|
| **Solid** | 2 (356), 1 (168), 40 slab (111), 7 (69), 3 (32), 6 (30), 4 (18), 62 (1), 65 (1) | 786 |
| **Hazard** | 9 ground pit (423), 8 spike (166), 103 small spike (14), 39 half spike (7) | 610 |
| **Ship portal** | 13 | 3 |
| **Cube portal** | 12 | 1 |
| Decoration (no collision) | 5 (661), 17/16/15 rods, 18–21 decorative spikes, 41 chains, 54 ball | 869 |
| Trigger (colour changes etc.; no collision) | 29, 30, 22, 23, 27 | 19 |
| Collectible (secret coins; ignored) | 142 | 3 |

- **No jump pads, orbs, speed portals, gravity portals, slopes or mini portals** ✅ (D6).
- **The decorative spikes (18–21) are not hazards.** These are the magenta background spikes in the video.
- **Rotation and flips:**
  - Hazards are only flipped vertically or rotated 180°. Their centred hitbox doesn't change.
  - Solids are rotated by ±90°; all solids used are 30 × 30 except the unrotated slabs.
  - So no hitbox rotation logic is needed for this level.
- **Confidence:** IDs 1–103 are classified from OpenGD's object table (high). Trigger IDs 22/23/27/29/30 and coin ID 142 aren't in that table and are classified from community knowledge (medium). They have no collision either way.

### Portals and timing (at 311.58 units/s)

| Portal | x | Level y | ≈ time | Matches video? |
|---|---|---|---|---|
| Ship | 7,995 | 165 | 25.7 s | ✅ (ship entered ≈ 25 s) |
| Cube | 12,555 | 149 | 40.3 s | ✅ (cube portal ≈ 40 s) |
| Ship | 22,935 | 149 | 73.6 s | Not in video |
| Ship (while already a ship: re-sets the bounds) | 24,045 | 315 | 77.2 s | Not in video |
| **Level end** | 26,384 | — | **84.7 s** | — |

**Overall validation (Step 1):** our engine is "correct" when:
1. the jump arc matches §3;
2. the bot can beat the converted Stereo Madness;
3. section timings match a playthrough video.
