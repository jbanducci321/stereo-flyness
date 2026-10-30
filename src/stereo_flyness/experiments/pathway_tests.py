"""The Step 0 pathway tests (docs/pathway_tests.md) as a list of runnable conditions.

`build_conditions` expands configs/pathway_tests.toml into `Condition`s: which neurons get
Poisson input, the input rate in every frame, what is watched and what is silenced. `run_trial`
runs one trial of one condition on the whole brain with `BrainStepper.run_frames` and saves
every frame's spike counts. Each trial is its own file, so an interrupted run resumes where it
stopped.

Saved per trial (`.npz`, see `load_trial`):
- spike counts per frame for every watched group (the fly's activity, unaltered);
- spike counts per frame for every neuron in the brain that fires at all, stored sparsely (D34);
- the input rate per frame for every input group (our stimulation, kept separate; hard rule 10);
- metadata: condition, sign version, seed, silenced IDs, git commit, frame length.
"""

import json
import os
import time
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

DT_MS = 0.1  # Brian2's default time step, which Shiu's model uses; run_trial checks it
SIGNS = ("original", "corrected")


@dataclass
class Condition:
    experiment: str  # "E1" ... "S3"
    name: str  # unique within a sign version, e.g. "E1/LC4_R+LPLC2_R/150Hz"
    sign: str  # "original" or "corrected" connectivity (D27)
    inputs: dict[str, list[int]]  # input group -> FlyWire IDs
    schedule: list[tuple[int, dict[str, float]]]  # (n_frames, Hz per input group), in order
    watch: dict[str, list[int]]  # watched group -> FlyWire IDs
    silence: list[int] = field(default_factory=list)
    trials: int = 10
    side: str = "right"  # stimulated side: "right", "left" or "both"

    @property
    def key(self) -> str:
        return f"{self.sign}/{self.name}"

    @property
    def n_frames(self) -> int:
        return sum(n for n, _ in self.schedule)

    def seed(self, base_seed: int, trial: int) -> int:
        """Stable per-trial seed. It ignores the sign version, so original and corrected runs
        of the same condition get the same Poisson input draws (a paired comparison)."""
        return zlib.crc32(f"{base_seed}/{self.name}/{trial}".encode()) & 0x7FFFFFFF

    def rates(self) -> np.ndarray:
        """Input rate (Hz) of every input group in every frame, shape (frames, groups)."""
        names = list(self.inputs)
        rows = [[seg.get(g, 0.0) for g in names] for n, seg in self.schedule for _ in range(n)]
        return np.asarray(rows, dtype=float).reshape(-1, len(names))

    def path(self, out_dir: Path, trial: int) -> Path:
        slug = self.name.replace("/", "__").replace("%", "pct")
        return Path(out_dir) / self.sign / self.experiment / slug / f"trial_{trial:02d}.npz"


class BaselineError(RuntimeError):
    """A trial with no input produced spikes, which means something is broken (D30)."""


def frame_steps(frame_ms: float) -> int:
    """Whole time steps per frame, as `BrainStepper.run_frames` rounds it."""
    return int(round(frame_ms / DT_MS))


def n_frames(duration_ms: float, frame_ms: float) -> int:
    return max(1, int(round(duration_ms / (frame_steps(frame_ms) * DT_MS))))


def _tag(rate):
    return f"{rate:g}Hz"


SIDE_TAG = {"right": "R", "left": "L", "both": "B"}


def judged(cond: Condition, cfg: dict) -> bool:
    """Whether D29-D31 judge this condition: the main side's tests, not recruitment or probes."""
    return cond.side == cfg["stim_side"] and not cond.experiment.startswith("P")


LOOM_TYPES = ("LC4", "LPLC2")


def loom_patches(con, cells, seed: int) -> dict[str, dict[str, list[int]]]:
    """Per side and looming type, every neuron in the order a "nearby" patch grows (P5).

    There are no visual-field positions, so "nearby" means sharing input partners
    (`input_similarity`). LC4 and LPLC2 share almost none, so each type grows its own patch:
    LC4 from a random neuron, LPLC2 from the LPLC2 neuron whose inputs are most like that one's.
    """
    from stereo_flyness.brain.celltypes import grow_order, input_similarity

    out = {}
    for side in ("right", "left"):
        lc4, lplc2 = (cells.ids(t, side=side) for t in LOOM_TYPES)
        sim = input_similarity(con, lc4 + lplc2)
        rng = np.random.default_rng([seed, zlib.crc32(side.encode())])
        a = int(rng.integers(len(lc4)))
        b = int(np.argmax(sim[a, len(lc4):]))
        n = len(lc4)
        out[side] = {"LC4": [lc4[i] for i in grow_order(sim[:n, :n], a)],
                     "LPLC2": [lplc2[i] for i in grow_order(sim[n:, n:], b)]}
    return out


def build_conditions(cfg: dict, cells, gf_partners: dict[str, list[int]],
                     sugar_ids: list[int], patches: dict | None = None) -> list[Condition]:
    """Every condition in the config.

    `cells` is a `CellTypes`; `gf_partners` maps "R"/"L" to the Giant Fiber's top input
    partners (E6); `sugar_ids` are the 21 right sugar GRNs (E4 control); `patches` is
    `loom_patches(...)`, needed only for probe P5.

    The main pathway tests stimulate `stim_side` (the right side; judged by D29-D31). The
    `[recruitment]` table repeats the game-input experiments on other sides ("left", or "both"
    sides at once), to find every neuron the game's inputs recruit for the subcircuit (D36).
    The `[probes]` table adds game-like tests that are never used to build a subcircuit (D36).
    """
    fr = cfg["frame_ms"]
    rates = cfg["rates_hz"]
    conds = []
    esc, st = cfg["escape"], cfg["steering"]
    n_esc, n_st = n_frames(esc["duration_ms"], fr), n_frames(st["duration_ms"], fr)
    for sign in st["signs"]:
        if sign not in SIGNS:
            raise ValueError(f"Unknown sign version {sign!r}")

    def ids(*types, side):
        if side == "both":
            return sorted(cells.ids(*types, side="right") + cells.ids(*types, side="left"))
        return cells.ids(*types, side=side)

    esc_watch = {
        "GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left"),
        "GF_partners_R": gf_partners["R"], "GF_partners_L": gf_partners["L"],
    }
    vs = [f"VS{i}" for i in range(1, 9)]
    st_watch = {}
    for name, sd in (("R", "right"), ("L", "left")):
        st_watch |= {f"VS_{name}": cells.ids(*vs, side=sd), f"DNp20_{name}": cells.ids("DNp20", side=sd),
                     f"DNp22_{name}": cells.ids("DNp22", side=sd), f"LPi09_{name}": cells.ids("LPi09", side=sd)}

    def add_side(side, trials, experiments, primary):
        s = SIDE_TAG[side]
        want = lambda exp: experiments is None or exp in experiments  # noqa: E731

        # --- Escape (original signs only, D27) ---
        lc4, lplc2 = f"LC4_{s}", f"LPLC2_{s}"
        groups = {lc4: ids("LC4", side=side), lplc2: ids("LPLC2", side=side)}
        both = {lc4: groups[lc4], lplc2: groups[lplc2]}

        def escape(exp, name, inputs, schedule, silence=(), n_trials=trials):
            if want(exp):
                conds.append(Condition(exp, f"{exp}/{name}", "original", inputs, schedule,
                                       {**esc_watch, **inputs}, sorted(silence), n_trials, side))

        for stim in ([lc4], [lplc2], [lc4, lplc2]):
            for r in rates:  # E1, with E6's partners watched throughout
                escape("E1", f"{'+'.join(stim)}/{_tag(r)}", {g: groups[g] for g in stim},
                       [(n_esc, {g: r for g in stim})])

        e2 = esc["e2"]
        n_on, n_off = n_frames(e2["on_ms"], fr), n_frames(e2["off_ms"], fr)
        for r in e2["rates_hz"]:
            cycle = [(n_on, {lc4: r, lplc2: r}), (n_off, {})]
            escape("E2", f"{lc4}+{lplc2}/onoff/{_tag(r)}", both, cycle * e2["cycles"])

        e3 = esc["e3"]
        # The main side keeps its original subsets; other sides get their own random stream
        rng = np.random.default_rng(e3["subset_seed"] if primary else [e3["subset_seed"], zlib.crc32(side.encode())])
        for frac in e3["fractions"]:
            k = max(1, int(round(frac * len(groups[lc4]))))
            full = k == len(groups[lc4])
            for sub in range(1 if full else e3["subsets"]):
                chosen = groups[lc4] if full else sorted(rng.choice(groups[lc4], k, replace=False).tolist())
                escape("E3", f"{lc4}_{frac:.0%}/subset{sub}/{_tag(e3['rate_hz'])}", {lc4: chosen},
                       [(n_esc, {lc4: e3["rate_hz"]})],
                       n_trials=trials if full else min(trials, e3["trials_per_subset"]))

        if primary:  # controls and the no-input baseline: main side only
            r4 = esc["e4"]["rate_hz"]
            escape("E4", "none/0Hz", both, [(n_esc, {})])  # baseline: input groups exist, at 0 Hz
            escape("E4", f"LC10a_{s}/{_tag(r4)}", {f"LC10a_{s}": cells.ids("LC10a", side=side)},
                   [(n_esc, {f"LC10a_{s}": r4})])
            escape("E4", f"sugar_{s}/{_tag(r4)}", {f"sugar_{s}": list(sugar_ids)},
                   [(n_esc, {f"sugar_{s}": r4})])

        e5 = esc["e5"]
        r5 = e5["rate_hz"]  # E5a was dropped (D35): E1's all-neuron record answers it
        escape("E5b", f"{lc4}+{lplc2}/inhibitory_partners_silenced/{_tag(r5)}", both,
               [(n_esc, {lc4: r5, lplc2: r5})], silence=cells.ids(*e5["inhibitory_partners"]))
        escape("E5c", f"{lc4}+{lplc2}/excitatory_partners_silenced/{_tag(r5)}", both,
               [(n_esc, {lc4: r5, lplc2: r5})], silence=cells.ids(*e5["excitatory_partners"]))

        # --- Steering (every sign version, D27) ---
        down, up, horiz = f"down_{s}", f"up_{s}", f"horizontal_{s}"
        sgroups = {down: ids("T4d", "T5d", side=side), up: ids("T4c", "T5c", side=side),
                   horiz: ids("T4a", "T4b", "T5a", "T5b", side=side)}

        for sign in st["signs"]:
            def steer(exp, name, inputs, schedule):
                if want(exp):
                    conds.append(Condition(exp, f"{exp}/{name}", sign, inputs, schedule,
                                           {**st_watch, **inputs}, [], trials, side))

            if primary:
                steer("S0", "none/0Hz", {down: sgroups[down], up: sgroups[up]}, [(n_st, {})])
            for g in (down, up):
                for r in rates:
                    steer("S1", f"{g}/{_tag(r)}", {g: sgroups[g]}, [(n_st, {g: r})])
            r3 = st["s3"]["rate_hz"]
            steer("S3", f"{horiz}/{_tag(r3)}", {horiz: sgroups[horiz]}, [(n_st, {horiz: r3})])
            # Round 2 (D32): the half-of-maximum "down" rate, once picked, adds S2 and a second S3
            if (d := st.get("half_max_rate_hz", {}).get(sign)) is not None:
                for r in [0, *rates]:
                    steer("S2", f"{down}_{_tag(d)}+{up}/{_tag(r)}", {down: sgroups[down], up: sgroups[up]},
                          [(n_st, {down: d, up: r})])
                if d != r3:
                    steer("S3", f"{horiz}/{_tag(d)}", {horiz: sgroups[horiz]}, [(n_st, {horiz: d})])

    add_side(cfg["stim_side"], cfg["trials"], None, primary=True)
    rec = cfg.get("recruitment", {})
    for side in rec.get("sides", []):
        add_side(side, rec["trials"], set(rec["experiments"]), primary=False)
    conds += probe_conditions(cfg, ids, esc_watch, st_watch, patches)

    names = [c.key for c in conds]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate condition names")
    return conds


def _ramp(n, top):
    """Rate rising linearly from top/n to top over n frames, as per-frame schedule steps."""
    return [top * (i + 1) / n for i in range(n)]


def patch_steps(n: int, first: float, total: int, steps: int) -> list[int]:
    """How many of a type's `n` neurons are on at each step of a growing patch: the side's patch
    grows geometrically from `first` of its `total` looming neurons to all of them, shared out
    between types by size; every step adds at least one neuron."""
    counts = []
    for k in range(steps):
        frac = (first / total) ** (1 - k / (steps - 1))
        c = max(1, int(round(frac * n)), counts[-1] + 1 if counts else 0)
        counts.append(min(n, c))
    counts[-1] = n
    return counts


def probe_conditions(cfg, ids, esc_watch, st_watch, patches=None) -> list[Condition]:
    """Game-like probe tests (`[probes]` in the config): held out from every subcircuit build (D36).

    - P1 "expanding looming": a side's LC4 + LPLC2 split into random chunks that switch on one
      after another (more neurons as an obstacle grows), then all off; repeated.
    - P2 "looming ramp": all of a side's LC4 + LPLC2, with the rate ramping up, then off; repeated.
    - P3 "up/down switching": downward and upward motion alternating.
    - P4 "steering over scrolling": constant horizontal motion with downward motion on and off.
    - P5 "spatial looming": a patch of LC4 + LPLC2 that grows outward from a few neurons
      (`loom_patches`), geometrically; with both sides, each side's patch grows at once.
    - P6 "looming over scrolling": P1's looming plus constant front-to-back motion (T4a + T5a),
      on both sign versions, watching escape and steering groups. No other test combines them.
    - P7 "close obstacles": all of a side's LC4 + LPLC2, short bursts close together.
    """
    pr = cfg.get("probes")
    if not pr:
        return []
    fr = cfg["frame_ms"]
    nf = lambda ms: n_frames(ms, fr)  # noqa: E731
    conds = []
    for side in pr["sides"]:
        s = SIDE_TAG[side]
        looming = ids("LC4", "LPLC2", side=side)

        def escape(exp, name, inputs, schedule):
            conds.append(Condition(exp, f"{exp}/{name}", "original", inputs, schedule,
                                   {**esc_watch, **inputs}, [], pr["trials"], side))

        p1 = pr["p1"]
        rng = np.random.default_rng([p1["seed"], zlib.crc32(side.encode())])
        chunks = np.array_split(rng.permutation(looming), p1["chunks"])
        p1_inputs = {f"loom_{s}_{k}": sorted(int(i) for i in c) for k, c in enumerate(chunks)}
        step = nf(p1["step_ms"])
        p1_cycle = [(step, {g: p1["rate_hz"] for g in list(p1_inputs)[:k + 1]}) for k in range(p1["chunks"])]
        p1_cycle = (p1_cycle + [(nf(p1["off_ms"]), {})]) * p1["repeats"]
        escape("P1", f"loom_{s}/expanding/{_tag(p1['rate_hz'])}", p1_inputs, p1_cycle)

        p2 = pr["p2"]
        g = f"loom_{s}"
        cycle = [(1, {g: r}) for r in _ramp(nf(p2["ramp_ms"]), p2["top_hz"])] + [(nf(p2["off_ms"]), {})]
        escape("P2", f"{g}/ramp/{_tag(p2['top_hz'])}", {g: looming}, cycle * p2["repeats"])

        if p5 := pr.get("p5"):
            if patches is None:
                raise ValueError("Probe P5 needs loom_patches (pass patches= to build_conditions)")
            sides = ["right", "left"] if side == "both" else [side]
            new = [[] for _ in range(p5["steps"])]  # neurons switched on at each step
            for sd in sides:
                total = sum(len(patches[sd][t]) for t in LOOM_TYPES)
                for t in LOOM_TYPES:
                    order = patches[sd][t]
                    counts = patch_steps(len(order), p5["first_neurons"], total, p5["steps"])
                    for k, (lo, hi) in enumerate(zip([0, *counts], counts)):
                        new[k] += order[lo:hi]
            p5_inputs = {f"patch_{s}_{k}": sorted(int(i) for i in c) for k, c in enumerate(new)}
            step = nf(p5["step_ms"])
            cycle = [(step, {g: p5["rate_hz"] for g in list(p5_inputs)[:k + 1]}) for k in range(p5["steps"])]
            cycle += [(nf(p5["off_ms"]), {})]
            escape("P5", f"patch_{s}/growing/{_tag(p5['rate_hz'])}", p5_inputs, cycle * p5["repeats"])

        if p7 := pr.get("p7"):
            g = f"loom_{s}"
            cycle = [(nf(p7["on_ms"]), {g: p7["rate_hz"]}), (nf(p7["off_ms"]), {})]
            escape("P7", f"{g}/bursts/{_tag(p7['rate_hz'])}", {g: looming}, cycle * p7["cycles"])

        down, up, horiz = f"down_{s}", f"up_{s}", f"horizontal_{s}"
        motion = {down: ids("T4d", "T5d", side=side), up: ids("T4c", "T5c", side=side),
                  horiz: ids("T4a", "T4b", "T5a", "T5b", side=side)}
        for sign in cfg["steering"]["signs"]:
            def steer(exp, name, inputs, schedule):
                conds.append(Condition(exp, f"{exp}/{name}", sign, inputs, schedule,
                                       {**st_watch, **inputs}, [], pr["trials"], side))

            p3 = pr["p3"]
            seg = nf(p3["segment_ms"])
            cycle = [(seg, {down: p3["rate_hz"]}), (seg, {up: p3["rate_hz"]})]
            steer("P3", f"{down}+{up}/switching/{_tag(p3['rate_hz'])}", {down: motion[down], up: motion[up]},
                  cycle * p3["cycles"] + [(seg, {})])

            p4 = pr["p4"]
            on, off = nf(p4["on_ms"]), nf(p4["off_ms"])
            cycle = [(on, {horiz: p4["horizontal_hz"], down: p4["down_hz"]}), (off, {horiz: p4["horizontal_hz"]})]
            steer("P4", f"{horiz}_{_tag(p4['horizontal_hz'])}+{down}/onoff/{_tag(p4['down_hz'])}",
                  {horiz: motion[horiz], down: motion[down]}, cycle * p4["cycles"])

            if p6 := pr.get("p6"):
                ftb = f"front_to_back_{s}"
                inputs = {**p1_inputs, ftb: ids(*p6["types"], side=side)}
                schedule = [(n, {**r, ftb: p6["horizontal_hz"]}) for n, r in p1_cycle]
                conds.append(Condition("P6", f"P6/loom_{s}+{ftb}_{_tag(p6['horizontal_hz'])}/expanding/"
                                       f"{_tag(p1['rate_hz'])}", sign, inputs, schedule,
                                       {**esc_watch, **st_watch, **inputs}, [], pr["trials"], side))
    return conds


def run_trial(cond: Condition, trial: int, out_dir, path_comp, path_con, base_seed: int,
              frame_ms: float, meta: dict | None = None) -> Path:
    """Run one trial and save it. Returns the saved path; skips work if it already exists."""
    from brian2 import Hz, defaultclock, ms

    from stereo_flyness.brain.stepper import BrainStepper

    path = cond.path(out_dir, trial)
    if path.exists():
        return path
    if abs(float(defaultclock.dt / ms) - DT_MS) > 1e-9:
        raise RuntimeError(f"Expected dt = {DT_MS} ms")

    seed = cond.seed(base_seed, trial)
    t0 = time.perf_counter()
    stepper = BrainStepper(path_comp, path_con, inputs=cond.inputs, watch=cond.watch, seed=seed,
                           silence=cond.silence)
    build_s = time.perf_counter() - t0

    rates = cond.rates()
    names = list(cond.inputs)
    baseline = not rates.any()  # no input at all: every neuron must stay silent (D30)
    counts = {g: np.zeros((cond.n_frames, len(ids)), dtype=np.uint16) for g, ids in cond.watch.items()}
    active = []  # (frame, model indices, counts) for every neuron that fired in that frame (D34)

    def set_frame_rates(i):
        for j, g in enumerate(names):
            stepper.set_rate(g, rates[i, j] * Hz)

    def on_frame(i, frame_counts):
        for g, c in frame_counts.items():
            counts[g][i] = c
        nz = np.flatnonzero(stepper.last_counts)
        if len(nz):
            active.append((i, nz, stepper.last_counts[nz]))
        if i + 1 < cond.n_frames:
            set_frame_rates(i + 1)

    set_frame_rates(0)
    t0 = time.perf_counter()
    stepper.run_frames(cond.n_frames, frame_steps(frame_ms) * DT_MS * ms, on_frame)
    run_s = time.perf_counter() - t0
    if baseline and active:
        n = sum(int(c.sum()) for _, _, c in active)
        raise BaselineError(f"{cond.key} trial {trial}: {n} spikes with no input. Shiu's model has "
                            "no internal noise, so this is a bug. Stopping the round (D30).")

    info = {
        **(meta or {}), "condition": asdict(cond) | {"schedule": cond.schedule}, "key": cond.key,
        "trial": trial, "seed": seed, "sign": cond.sign, "path_con": Path(path_con).name,
        "frame_ms": frame_steps(frame_ms) * DT_MS, "n_frames": cond.n_frames,
        "build_s": round(build_s, 2), "run_s": round(run_s, 2),
    }
    arrays = {"rates": rates, "input_names": np.array(names), "meta": np.array(json.dumps(info))}
    frames = np.concatenate([np.full(len(nz), i) for i, nz, _ in active]) if active else np.zeros(0)
    neurons = np.concatenate([nz for _, nz, _ in active]) if active else np.zeros(0, dtype=int)
    spikes = np.concatenate([c for _, _, c in active]) if active else np.zeros(0)
    active_idx, which = np.unique(neurons, return_inverse=True)
    arrays |= {"all_ids": stepper.flyids[active_idx], "all_frame": frames.astype(np.uint16),
               "all_neuron": which.astype(np.int32), "all_count": spikes.astype(np.uint16)}
    for g, ids in cond.watch.items():
        arrays[f"spikes__{g}"] = counts[g]
        arrays[f"ids__{g}"] = np.asarray(ids, dtype=np.int64)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with open(tmp, "wb") as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)  # a trial file only ever appears complete
    return path


def load_trial(path) -> dict:
    """A saved trial: {"meta", "rates", "input_names", "spikes": {group: (frames, neurons)},
    "ids": {group: FlyWire IDs}, "all_ids", "all_spikes"}.

    `all_spikes` is (frames, len(all_ids)): every neuron that fired at least once in the trial,
    rebuilt from the sparse records (D34). Neurons not in `all_ids` never fired.
    """
    with np.load(path) as z:
        out = {"meta": json.loads(str(z["meta"])), "rates": z["rates"],
               "input_names": [str(n) for n in z["input_names"]], "spikes": {}, "ids": {}}
        n_frames = out["rates"].shape[0]
        out["all_ids"] = z["all_ids"]
        out["all_spikes"] = np.zeros((n_frames, len(z["all_ids"])), dtype=np.uint16)
        out["all_spikes"][z["all_frame"].astype(int), z["all_neuron"]] = z["all_count"]
        for k in z.files:
            if k.startswith("spikes__"):
                out["spikes"][k[8:]] = z[k]
            elif k.startswith("ids__"):
                out["ids"][k[5:]] = z[k]
    return out
