# CLAUDE.md

Before doing anything in this repo, read **[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)** (full project context, decisions, task list) and **[docs/decisions.md](docs/decisions.md)** (the canonical decision log). Treat the decisions there as settled unless the human explicitly asks to change one.

**Project:** a FlyWire v783 connectome model of the fruit fly brain (Shiu et al. 2024, Brian2) drives a minimal Geometry Dash–style game. Connectome weights are frozen; only 2–3 interface dials are tuned. Stereo Madness is the held-out final test.

**Team:**
- Jacob (`jbanducci321`): engineering.
- Shannyn (`shancabi`, she/her): neuroscience.
- Each person works on their own branch. `main` is protected: changes need a PR with 1 approval.

## Hard rules
1. Never modify connectome weights or edit `src/stereo_flyness/brain/shiu_model.py`, `shiu_utils.py` or `SHIU_LICENSE.txt` (vendored unchanged).
2. Never commit `data/` (except `data/README.md`), `results/` or any Geometry Dash level data.
3. Never commit or push to `main`. Use a branch and a PR.
4. Check every FlyWire ID against v783 (`data/Completeness_783.csv`). IDs change between releases.
5. Never tune on Stereo Madness, or shape the training generators from its layout.
6. Our design choices live in `src/stereo_flyness/interface/` and get logged in `docs/decisions.md`.
7. Don't copy code from camila314/gdp, pathfinder (unlicensed) or eonsystemspbc/fly-brain (GPL). Read them for facts only.
8. Ask the human before big or irreversible choices, before changing a decision, or before touching the other person's task area.
9. Be scientifically honest. Push back when something is wrong.
10. Closed-loop runs log every frame for the replay viewer (D19). Replays show recorded activity unaltered and label our input encoding separately from the fly's spikes.

## Commands
```bash
uv sync
uv run pytest                              # first run ~5 min (Brian2 compiles), then ~20 s
uv run python scripts/download_data.py     # ~104 MB, checksum-verified
```
Windows: Brian2 needs Microsoft C++ Build Tools ("Desktop development with C++"). If it reports that MSVC is missing, Resume or Repair the install in the Visual Studio Installer.
