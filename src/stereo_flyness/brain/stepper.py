"""Closed-loop stepping for the Shiu et al. (2024) model.

Shiu's ``run_trial`` builds the network, runs it once with fixed Poisson input, then throws it
away. The game needs the opposite: build the brain once, advance it one frame at a time,
change the input between frames, and read spikes back after each one. ``BrainStepper`` does
this without touching the model. The network comes from ``shiu_model.create_model``, and only
the way external input is delivered differs (see ``BrainStepper._build_inputs``).
"""

import numpy as np
import pandas as pd
from brian2 import Hz, Network, PoissonGroup, SpikeMonitor, Synapses, defaultclock, ms, network_operation
from brian2 import seed as set_seed

from stereo_flyness.brain.shiu_model import create_model, default_params


class BrainStepper:
    """Shiu's whole-brain model, built once and advanced in short steps.

    Parameters
    ----------
    path_comp, path_con
        Completeness CSV and connectivity parquet, the same files Shiu's code uses.
    inputs : dict[str, list[int]]
        Named groups of FlyWire IDs that can receive Poisson stimulation, e.g.
        ``{"sugar": [...]}``. Rates start at 0 Hz; change them with `set_rate`.
    watch : dict[str, list[int]]
        Named groups of FlyWire IDs whose spikes `step` reports, e.g. ``{"mn9": [...]}``.
    params : dict
        Model constants and equations. Defaults to Shiu's.
    seed : int, optional
        Seed for Brian2's random number generators, for reproducible runs.
    """

    def __init__(self, path_comp, path_con, inputs, watch, params=default_params, seed=None):
        if seed is not None:
            set_seed(seed)
        self.params = params

        flyids = pd.read_csv(path_comp, index_col=0).index
        self._flyid2i = {f: i for i, f in enumerate(flyids)}
        # Check every ID before the (slow) network build.
        input_idx = {name: self._indices(ids) for name, ids in inputs.items()}
        self._watch = {name: self._indices(ids) for name, ids in watch.items()}

        # Shiu's network, unchanged. Their all-spike monitor is dropped in favour of counts.
        self.neurons, synapses, _ = create_model(path_comp, path_con, params)
        self._poisson, input_synapses, self._input_slices = self._build_inputs(input_idx)

        # record=False keeps only per-neuron spike counts, so memory stays constant however
        # long the brain runs.
        self._spk_mon = SpikeMonitor(self.neurons, record=False)
        self._last_count = np.zeros(len(flyids), dtype=int)

        self.net = Network(self.neurons, synapses, self._poisson, input_synapses, self._spk_mon)

    def _indices(self, ids):
        missing = [f for f in ids if f not in self._flyid2i]
        if missing:
            raise KeyError(f"FlyWire IDs not in this connectome: {missing}")
        return np.array([self._flyid2i[f] for f in ids], dtype=int)

    def _build_inputs(self, input_idx):
        """Poisson input equivalent to Shiu's, but with rates that can change between steps.

        Shiu's ``poi`` gives each stimulated neuron its own PoissonInput (N=1). On each event
        it adds ``w_syn * f_poi`` to v, and its rate is fixed when the network is built. Here
        each stimulated neuron instead gets its own PoissonGroup source, connected one-to-one
        with the same weight and target variable. Events land in the same 'synapses' slot of
        the time step they are drawn in.

        A PoissonGroup fires with probability ``rate * dt`` per step. That's the same
        distribution as PoissonInput's Binomial(1, rate * dt), but the rate can be reassigned
        at any time. As in Shiu's code, stimulated neurons get no refractory period.
        """
        slices, targets = {}, []
        for name, idx in input_idx.items():
            slices[name] = slice(len(targets), len(targets) + len(idx))
            targets.extend(idx)
        if not targets:
            raise ValueError("At least one input group with one neuron is required.")
        targets = np.asarray(targets, dtype=int)

        poisson = PoissonGroup(len(targets), rates=0 * Hz)
        synapses = Synapses(
            poisson, self.neurons, on_pre="v += w_in",
            namespace={"w_in": self.params["w_syn"] * self.params["f_poi"]},
        )
        synapses.connect(i=np.arange(len(targets)), j=targets)
        self.neurons.rfc[targets] = 0 * ms
        return poisson, synapses, slices

    @property
    def t(self):
        """Total simulated time so far."""
        return self.net.t

    def set_rate(self, name, rate):
        """Set the Poisson rate of input group `name`: one rate for all its neurons, or one each."""
        self._poisson.rates[self._input_slices[name]] = rate

    def step(self, duration):
        """Advance the brain by `duration`, rounded to whole time steps (dt = 0.1 ms by default).

        Returns each watched group's spike counts during this step, as arrays in the order its
        IDs were given.
        """
        n_dt = int(round(float(duration / defaultclock.dt)))
        self.net.run(n_dt * defaultclock.dt)
        return self._read_counts()

    def run_frames(self, n_frames, frame, on_frame):
        """Advance `n_frames` frames of length `frame` in a single Brian2 run.

        After each frame, ``on_frame(i, counts)`` is called with the frame index and that
        frame's watched spike counts (the same dict `step` returns). It may call `set_rate`
        to change the input for the following frame.

        This is the fast path for closed-loop use. Every `step` call is a separate
        ``Network.run``, which makes Brian2 regenerate its code objects (about 100-200 ms
        each time, whatever the network size). This pays that cost once. The results are
        identical to calling `step(frame)` in a loop.
        """
        n_dt = int(round(float(frame / defaultclock.dt)))
        frame_dt = n_dt * defaultclock.dt
        if int(round(float(self.net.t / defaultclock.dt))) % n_dt:
            raise ValueError("run_frames must start at a multiple of the frame length.")

        state = {"i": 0, "first": True}

        # 'start' slot of each frame-boundary time step = after exactly k frames of
        # simulation. The call at the very start of the run has no finished frame to report.
        @network_operation(dt=frame_dt, when="start")
        def _frame_boundary():
            if state["first"]:
                state["first"] = False
                return
            on_frame(state["i"], self._read_counts())
            state["i"] += 1

        self.net.add(_frame_boundary)
        try:
            self.net.run(n_frames * frame_dt)
        finally:
            self.net.remove(_frame_boundary)
        on_frame(state["i"], self._read_counts())  # the last frame ends with the run

    def _read_counts(self):
        count = np.asarray(self._spk_mon.count[:])
        new, self._last_count = count - self._last_count, count
        return {name: new[idx] for name, idx in self._watch.items()}
