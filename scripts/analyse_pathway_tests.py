"""Judge the pathway tests (J4, checkpoint 4) by the rules agreed before round 1 (D28-D35).

Reads every saved trial in results/pathway_tests/, applies the go/no-go rules, picks round 2's
rates (D32), and writes a report to results/pathway_tests/analysis/report.md (git-ignored),
plus a per-trial CSV. Rules that need round 2 are marked as waiting for it.

Usage:
    uv run python scripts/analyse_pathway_tests.py
"""

import math
import sys
import tomllib
from collections import Counter

import numpy as np
import pandas as pd

from find_target_neurons import fetch_annotations
from run_pathway_tests import CONFIG, OUT, PATH_CON, conditions
from stereo_flyness.experiments.pathway_analysis import (
    by_rate, escape_rules, horizontal_rule, latency_rule, onoff_cycles, pick_e2_rate, pick_half_max,
    reliable, steering_rules, trial_row,
)
from stereo_flyness.experiments.pathway_tests import load_trial

REPORT = OUT / "analysis" / "report.md"


def md_table(df: pd.DataFrame, digits: int = 1) -> str:
    def fmt(v):
        if isinstance(v, (bool, np.bool_)):
            return "yes" if v else "no"
        if isinstance(v, (float, np.floating)):
            return "–" if math.isnan(v) else ("inf" if math.isinf(v) else f"{v:.{digits}f}")
        return str(v)
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def ms(series) -> str:
    return f"{series.mean():.1f} ± {series.std(ddof=1):.1f}" if len(series) > 1 else f"{series.mean():.1f}"


def verdict(ok) -> str:
    return "**PASS**" if ok else "**FAIL**"


def load_all(conds, out_dir):
    rows, trials = [], {}
    for c in conds:
        for t in range(c.trials):
            p = c.path(out_dir, t)
            if not p.exists():
                continue
            tr = load_trial(p)
            trials[(c.key, t)] = tr
            parts = c.name.split("/")
            rows.append({**trial_row(tr), "experiment": c.experiment, "sign": c.sign, "name": c.name,
                         "group": parts[1], "rate": float(parts[-1][:-2]),
                         "commit": tr["meta"]["commit"]})
    return pd.DataFrame(rows), trials


def analyse(out_dir, cfg, conds, title="# Pathway tests: analysis") -> dict:
    """Judge the trials saved under `out_dir` (whole brain or a subcircuit). Returns the report
    lines, the verdicts and the per-trial table."""
    by_key = {c.key: c for c in conds}
    df, trials = load_all(conds, out_dir)
    ann = pd.read_csv(fetch_annotations(), sep="\t", usecols=["root_id", "cell_type", "side"], low_memory=False)
    ctype = dict(zip(ann["root_id"].astype("int64"), ann["cell_type"].fillna("?")))
    cside = dict(zip(ann["root_id"].astype("int64"), ann["side"].fillna("?")))
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"])

    out = [title, "",
           "Rules: D28–D35 in `docs/decisions.md`, agreed before round 1. Rates are mean Hz per neuron; ± is the SD across trials.",
           "Latencies are to the end of the 4.2 ms frame holding the first spike (upper bounds).", ""]

    # --- Integrity ---
    expected = Counter(c.experiment for c in conds for _ in range(c.trials))
    found = Counter(df["experiment"])
    commits = sorted(set(df["commit"]))
    base = df[df["name"].str.endswith("none/0Hz")]
    base_spikes = sum(int(trials[(k, t)]["all_spikes"].sum()) for k, t in zip(base["key"], base["trial"]))
    out += ["## Run integrity", "",
            md_table(pd.DataFrame([{"experiment": e, "expected": expected[e], "found": found.get(e, 0)}
                                   for e in sorted(expected)])), "",
            f"- Commits: {', '.join(c[:12] for c in commits)}" + (" (**dirty**)" if any("dirty" in c for c in commits) else " (clean)"),
            f"- No-input baselines ({len(base)} trials, E4 + S0): {base_spikes} spikes in the whole brain. "
            f"D30 requires 0: {verdict(base_spikes == 0)}", ""]

    # --- Escape ---
    e1 = df[df["experiment"] == "E1"]
    out += ["## Escape: LC4 / LPLC2 → Giant Fiber", "", "### E1 dose–response (all three input groups)", ""]
    rows = []
    for (g, r), d in e1.groupby(["group", "rate"]):
        rows.append({"input": g, "rate Hz": int(r), "GF right": ms(d["rate:GF_R"]), "GF left": ms(d["rate:GF_L"]),
                     "right/left": d["rate:GF_R"].mean() / d["rate:GF_L"].mean() if d["rate:GF_L"].mean() else math.inf,
                     "trials right fires": f"{int(d['fires:GF_R'].sum())}/{len(d)}",
                     "trials left fires": f"{int(d['fires:GF_L'].sum())}/{len(d)}",
                     "first spike ms (median)": d["gf_first_ms"].median()})
    out += [md_table(pd.DataFrame(rows)), ""]

    both = e1[e1["group"] == "LC4_R+LPLC2_R"]
    esc = escape_rules(both)
    out += ["### D29 escape rules (judged on LC4 + LPLC2)", "",
            f"- **Rule 0**, fires reliably at one or more rates: reliable at {[int(r) for r in esc['reliable_rates']]} Hz → {verdict(esc['rule0'])}",
            f"- **Rule 1**, rises with input: mean at 200 Hz − mean at 25 Hz = {esc['rise']:.1f} Hz; "
            f"bar (2 pooled SDs) = {esc['rise_bar']:.1f} Hz → {verdict(esc['rule1'])}",
            "- **Rule 2**, right beats left by > 2 pooled SDs at every reliable rate:", "",
            md_table(esc["side"].rename(columns={"diff": "right − left", "bar": "2 pooled SDs"})), "",
            f"  → {verdict(esc['rule2'])}", ""]

    e2_rate, e2_ok = pick_e2_rate(both)
    out += ["### D32: E2's lower rate", "",
            f"- Lowest rate where the right Giant Fiber spikes within 100 ms in ≥ 9/10 trials: **{e2_rate} Hz**"
            + ("" if e2_ok else " (no rate qualified; 200 Hz used, per D32)"), ""]
    early = both.assign(early=both["gf_first_ms"] <= 100).groupby("rate")["early"].agg(["sum", "count"])
    out += [md_table(early.reset_index().rename(columns={"rate": "rate Hz", "sum": "trials spiking within 100 ms", "count": "trials"}), 0), ""]

    e2_keys = [c.key for c in conds if c.experiment == "E2"]
    out += ["### E2 latency and offset; D29 rule 3", "",
            "Rule 3 is applied at every E2 rate (D32's lower rate and 150 Hz) and must pass at each. "
            "With 4.2 ms frames, onset latencies are quantised to multiples of 4.2 ms, so an SD of 0 means "
            "every first spike fell in the same frame, not that latency is exactly constant.", ""]
    rule3 = []
    for k in e2_keys:
        cyc = pd.concat([onoff_cycles(trials[(k, t)]).assign(trial=t) for t in range(by_key[k].trials)
                         if (k, t) in trials], ignore_index=True)
        lat = latency_rule(cyc)
        rule3.append(lat["pass"])
        out += [f"- `{k}`: onset {lat['mean_ms']:.1f} ± {lat['sd_ms']:.1f} ms over {lat['cycles']} cycles "
                f"({lat['missed_cycles']} without a spike); offset {ms(cyc['offset_ms'])} ms "
                f"(max {cyc['offset_ms'].max():.1f}); spikes per 300 ms 'on' {ms(cyc['spikes_on'])}",
                f"  - D29 rule 3 at this rate: mean < 100 ms and 4 × SD = {4 * lat['sd_ms']:.1f} < 238 ms → {verdict(lat['pass'])}"]
    esc["rule3"] = bool(rule3) and all(rule3)
    out += ["", f"- **Rule 3**, at every E2 rate → {verdict(esc['rule3'])}", ""]

    # E3
    e3 = df[df["experiment"] == "E3"].copy()
    e3["fraction"] = e3["group"].str.extract(r"_(\d+)%")[0].astype(int)
    rows = []
    for f, d in e3.groupby("fraction"):
        rows.append({"LC4 fraction %": f, "neurons": len(by_key[d["key"].iloc[0]].inputs["LC4_R"]),
                     "trials": len(d), "GF right": ms(d["rate:GF_R"]), "GF left": ms(d["rate:GF_L"]),
                     "trials right fires": f"{int(d['fires:GF_R'].sum())}/{len(d)}",
                     "first spike ms (median)": d["gf_first_ms"].median(),
                     "subset means (right GF)": ", ".join(f"{v:.0f}" for v in d.groupby("name")["rate:GF_R"].mean())})
    out += ["## E3 recruitment (right LC4 only, 150 Hz)", "", md_table(pd.DataFrame(rows)), ""]

    # E4
    ref = both[both["rate"] == 150]["rate:GF_R"].mean()
    rows = []
    for name, d in df[df["experiment"] == "E4"].groupby("name"):
        rows.append({"control": name.split("/", 1)[1], "GF right": ms(d["rate:GF_R"]), "GF left": ms(d["rate:GF_L"]),
                     "% of looming response": 100 * d["rate:GF_R"].mean() / ref,
                     "trials with a GF spike (right)": f"{int(d['fires:GF_R'].sum())}/{len(d)}",
                     "trials with a GF spike (left)": f"{int(d['fires:GF_L'].sum())}/{len(d)}",
                     "quiet (< 10%)": d["rate:GF_R"].mean() < 0.1 * ref})
    out += ["## E4 specificity controls (D30)", "",
            f"Reference: right Giant Fiber with LC4 + LPLC2 at 150 Hz = {ref:.1f} Hz. "
            "A control above 10% is a model finding, not an escape failure.", "", md_table(pd.DataFrame(rows)), ""]

    # E5
    rows = [{"condition": "E1 reference (nothing silenced)", "GF right": ms(both[both['rate'] == 150]['rate:GF_R']),
             "GF left": ms(both[both['rate'] == 150]['rate:GF_L']),
             "first spike ms (median)": both[both["rate"] == 150]["gf_first_ms"].median()}]
    for name, d in df[df["experiment"].isin(["E5b", "E5c"])].groupby("name"):
        rows.append({"condition": name, "GF right": ms(d["rate:GF_R"]), "GF left": ms(d["rate:GF_L"]),
                     "first spike ms (median)": d["gf_first_ms"].median()})
    out += ["## E5 lesions (LC4 + LPLC2 at 150 Hz)", "", md_table(pd.DataFrame(rows)), ""]

    # E6 + left route (D34)
    k150 = by_key["original/E1/LC4_R+LPLC2_R/150Hz"]
    stim = {i for ids in k150.inputs.values() for i in ids}
    ts = [trials[(k150.key, t)] for t in range(k150.trials)]
    secs = ts[0]["meta"]["n_frames"] * ts[0]["meta"]["frame_ms"] / 1000
    rate = pd.concat([pd.Series(t["all_spikes"].sum(axis=0) / secs, index=t["all_ids"]) for t in ts], axis=1)
    rate = rate.fillna(0).mean(axis=1)  # mean over trials; absent = silent
    fly = rate[[i not in stim for i in rate.index]]
    out += ["## Whole-brain activity, E1 LC4 + LPLC2 at 150 Hz (D34)", "",
            f"- Neurons firing in at least one trial: {len(rate)}, of which {len(stim & set(rate.index))} are stimulated (our input) "
            f"and {len(fly)} are the fly's own response.",
            f"- Stimulated LC4/LPLC2 neurons are excluded from the tables below (hard rule 10).", ""]
    for side, gf in (("right", "GF_R"), ("left", "GF_L")):
        gf_id = k150.watch[gf][0]
        inp = con[con["Postsynaptic_ID"] == gf_id].groupby("Presynaptic_ID").agg(
            synapses=("Connectivity", "sum"), sign=("Excitatory", "first"))
        inp["rate Hz"] = [fly.get(i, 0.0) for i in inp.index]
        inp["signed drive"] = inp["rate Hz"] * inp["synapses"] * inp["sign"]
        active = inp[(inp["rate Hz"] > 0)].sort_values("signed drive", key=abs, ascending=False)
        top = active.head(12).reset_index()
        top.insert(1, "type", [ctype.get(i, "?") for i in top["Presynaptic_ID"]])
        top.insert(2, "side", [cside.get(i, "?") for i in top["Presynaptic_ID"]])
        top["sign"] = top["sign"].map({1: "+", -1: "−"})
        exc = active.loc[active["signed drive"] > 0, "signed drive"].sum()
        inh = -active.loc[active["signed drive"] < 0, "signed drive"].sum()
        out += [f"### Active inputs to the {side} Giant Fiber", "",
                f"{len(active)} of its {len(inp)} input neurons fire (not counting stimulated ones). "
                f"Drive = rate × synapses × sign (a rough ranking, not a model quantity). "
                f"Total excitatory drive {exc:,.0f}, inhibitory {inh:,.0f}.", "",
                md_table(top.rename(columns={"Presynaptic_ID": "FlyWire ID"}).astype({"FlyWire ID": str}), 1), ""]

    # --- Steering ---
    out += ["## Steering: T4/T5 → VS cells → DNp20 / DNp22", ""]
    picks, steer_go = {}, {}
    for sign in [s for s in cfg["steering"]["signs"] if s in set(df["sign"])]:
        s1 = df[(df["experiment"] == "S1") & (df["sign"] == sign)]
        st = steering_rules(s1, "down_R", "up_R")
        down = s1[s1["group"] == "down_R"]
        half, frac = pick_half_max(down)
        picks[sign] = half
        rows = []
        for (g, r), d in s1.groupby(["group", "rate"]):
            rows.append({"input": g, "rate Hz": int(r), "VS right": ms(d["rate:VS_R"]), "VS left": ms(d["rate:VS_L"]),
                         "DNp20 right": ms(d["rate:DNp20_R"]), "DNp22 right": ms(d["rate:DNp22_R"]),
                         "LPi09 right": ms(d["rate:LPi09_R"]),
                         "trials VS fires": f"{int(d['fires:VS_R'].sum())}/{len(d)}",
                         "trials DNp20 fires": f"{int(d['fires:DNp20_R'].sum())}/{len(d)}"})
        h150 = df[(df["experiment"] == "S3") & (df["sign"] == sign) & (df["rate"] == 150)]
        hr = horizontal_rule(down[down["rate"] == 150], h150)
        out += [f"### {sign} signs", "", md_table(pd.DataFrame(rows)), "",
                f"- **Rule 1**, down makes right VS and DNp20 fire reliably at one or more rates → {verdict(st['rule1'])}",
                f"- **Rule 2**, at such a rate, up gives VS and DNp20 < 10% of down → {verdict(st['rule2'])}", "",
                md_table(st["table"], 3), "",
                f"- **D32 half-of-maximum 'down' rate: {half} Hz** (right VS reaches {100 * frac:.0f}% of its sweep maximum)",
                f"- S3 at 150 Hz (reported only): right VS down {hr['down']:.1f} "
                f"vs horizontal {hr['horizontal']:.1f} Hz; difference {hr['diff']:.1f}, bar {hr['bar']:.1f} → "
                f"{'lower' if hr['pass'] else 'not clearly lower'}"]
        hh = df[(df["experiment"] == "S3") & (df["sign"] == sign) & (df["rate"] == half)]
        if len(hh):
            h3 = horizontal_rule(down[down["rate"] == half], hh)
            out += [f"- **Rule 3**, at the half-of-maximum rate ({half} Hz): right VS down {ms(down[down['rate'] == half]['rate:VS_R'])} "
                    f"vs horizontal {ms(hh['rate:VS_R'])} Hz; difference {h3['diff']:.1f}, bar (2 pooled SDs) {h3['bar']:.1f} "
                    f"→ {verdict(h3['pass'])}. Horizontal DNp20: {ms(hh['rate:DNp20_R'])} Hz "
                    f"(down: {ms(down[down['rate'] == half]['rate:DNp20_R'])})"]
            rule3_ok = h3["pass"]
        else:
            out += [f"- **Rule 3** is judged at {half} Hz in round 2 (not run yet)"]
            rule3_ok = None
        s2 = df[(df["experiment"] == "S2") & (df["sign"] == sign)]
        if len(s2):
            rows = []
            for r, d in s2.groupby("rate"):
                rows.append({"up rate Hz (down fixed)": int(r), "VS right": ms(d["rate:VS_R"]),
                             "DNp20 right": ms(d["rate:DNp20_R"]), "DNp22 right": ms(d["rate:DNp22_R"]),
                             "LPi09 right": ms(d["rate:LPi09_R"])})
            base = s2[s2["rate"] == 0]["rate:VS_R"].mean()
            top = s2[s2["rate"] == s2["rate"].max()]["rate:VS_R"].mean()
            out += ["", f"S2 opponent inhibition (reported, not part of the go/no-go): 'down' fixed at {half} Hz, "
                    f"'up' swept. Right VS goes from {base:.1f} Hz (down only) to {top:.1f} Hz at the highest 'up' rate "
                    f"({100 * (top - base) / base:+.0f}%).", "", md_table(pd.DataFrame(rows))]
        go = st["rule1"] and st["rule2"] and rule3_ok
        steer_go[sign] = go
        out += ["", f"- **Steering go/no-go ({sign})**: " + ("**GO**" if go else ("waiting for round 2" if rule3_ok is None else "**NO-GO**")), ""]

    esc_go = esc["rule0"] and esc["rule1"] and esc["rule2"] and esc["rule3"]
    carry = "original" if steer_go.get("original") else ("corrected (D28 fallback)" if steer_go.get("corrected") else "none")
    out += ["## Verdicts", "",
            f"- **Escape pathway (LC4/LPLC2 → Giant Fiber → cube jump): {'GO' if esc_go else 'NO-GO'}** "
            f"(rules 0–3: {', '.join(verdict(esc[f'rule{i}']).strip('*') for i in range(4))})",
            *(f"- **Steering pathway, {s} signs: {'GO' if g else 'NO-GO'}**" for s, g in steer_go.items()),
            f"- **Sign version carried forward (D28): {carry}**", ""]

    out += ["## Round 2 settings picked by D32", "",
            f"- `[escape.e2] rates_hz = [{e2_rate}, 150]`" if e2_rate != 150 else "- E2: 150 Hz already covers it",
            f"- `[steering.half_max_rate_hz] original = {picks.get('original')}, corrected = {picks.get('corrected')}`", ""]

    verdicts = {"escape": esc_go, **{f"escape_rule{i}": esc[f"rule{i}"] for i in range(4)},
                **{f"steering_{s}": g for s, g in steer_go.items()}, "carry": carry,
                "e2_rate": e2_rate, "half_max": picks}
    return {"lines": out, "verdicts": verdicts, "df": df, "trials": trials}


def main() -> None:
    cfg = tomllib.loads(CONFIG.read_text())
    res = analyse(OUT, cfg, conditions(cfg))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(res["lines"]), encoding="utf-8")
    res["df"].to_csv(REPORT.parent / "trials.csv", index=False)
    sys.stdout.reconfigure(encoding="utf-8")  # the report has arrows and ±; Windows consoles default to cp1252
    print("\n".join(res["lines"]))
    print(f"\nWrote {REPORT.relative_to(OUT.parents[1])} and trials.csv")


if __name__ == "__main__":
    main()
