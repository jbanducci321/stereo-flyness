"""Setup check: reproduce Shiu et al. (2024) sugar -> MN9 result on FlyWire v783.

Stimulates the 21 right-hemisphere labellar sugar-sensing gustatory receptor neurons (GRNs)
with Poisson input and measures the firing rate of MN9, the proboscis motor neuron the paper
shows is activated by sugar. Uses the unchanged Shiu model on the whole brain.

Reference (Shiu's stored example results, FlyWire v630, 30 trials):
    sugar GRNs at default rate  -> MN9 ~93 Hz
    sugar GRNs at 100 Hz        -> MN9 ~67 Hz
v783 is a later proofreading release, so we expect similar, not identical, rates.

Usage:
    uv run python scripts/reproduce_sugar.py --n-run 30 --n-proc 4
"""

import argparse
import time
from pathlib import Path

import pandas as pd
from brian2 import Hz

from stereo_flyness.brain.shiu_model import default_params, run_exp

ROOT = Path(__file__).resolve().parents[1]
PATH_COMP = ROOT / "data" / "Completeness_783.csv"
PATH_CON = ROOT / "data" / "Connectivity_783.parquet"
PATH_RES = ROOT / "results" / "sugar"

# Shiu's list (v630 IDs). 20 of 21 are unchanged in v783. 720575940620900446 was re-segmented
# and is replaced by its v783 ID 720575940639259967 (the same substitution used by
# eonsystemspbc/fly-brain; 95% of its downstream partners are shared with the other sugar GRNs).
SUGAR_GRNS_783 = [
    720575940624963786, 720575940630233916, 720575940637568838, 720575940638202345,
    720575940617000768, 720575940630797113, 720575940632889389, 720575940621754367,
    720575940621502051, 720575940640649691, 720575940639332736, 720575940616885538,
    720575940639198653, 720575940639259967, 720575940617937543, 720575940632425919,
    720575940633143833, 720575940612670570, 720575940628853239, 720575940629176663,
    720575940611875570,
]
MN9 = 720575940660219265  # same ID in v630 and v783

REFERENCE_MN9_HZ = {"default": 93.3, 100: 67.0}  # v630, from Shiu's results/example


def mn9_rates(path: Path, n_run: int, t_run_s: float) -> pd.Series:
    df = pd.read_parquet(path)
    per_trial = df[df["flywire_id"] == MN9].groupby("trial").size()
    return per_trial.reindex(range(n_run), fill_value=0) / t_run_s


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-run", type=int, default=30, help="trials per condition (paper: 30)")
    parser.add_argument("--n-proc", type=int, default=4, help="parallel worker processes (each holds the whole brain in memory)")
    parser.add_argument("--rates", default="default,100", help="comma-separated sugar GRN rates in Hz, or 'default'")
    args = parser.parse_args()

    PATH_RES.mkdir(parents=True, exist_ok=True)
    rows = []

    for rate in args.rates.split(","):
        params = dict(default_params)
        params["n_run"] = args.n_run
        key = "default" if rate == "default" else int(rate)
        if key != "default":
            params["r_poi"] = key * Hz
        exp_name = f"sugarR_{key}"

        start = time.perf_counter()
        run_exp(
            exp_name=exp_name, neu_exc=SUGAR_GRNS_783, path_res=PATH_RES,
            path_comp=PATH_COMP, path_con=PATH_CON, params=params,
            n_proc=args.n_proc, force_overwrite=True,
        )
        wall_s = time.perf_counter() - start

        t_run_s = float(params["t_run"])  # Brian2 quantities convert to SI units (seconds)
        rates = mn9_rates(PATH_RES / f"{exp_name}.parquet", args.n_run, t_run_s)
        n_active = pd.read_parquet(PATH_RES / f"{exp_name}.parquet")["flywire_id"].nunique()
        rows.append({
            "sugar_rate_hz": float(params["r_poi"] / Hz),
            "n_run": args.n_run,
            "mn9_rate_mean_hz": round(rates.mean(), 1),
            "mn9_rate_std_hz": round(rates.std(ddof=0), 1),
            "reference_v630_hz": REFERENCE_MN9_HZ.get(key),
            "active_neurons": n_active,
            "wall_time_s": round(wall_s, 1),
            "n_proc": args.n_proc,
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(PATH_RES / "summary.csv", index=False)
    print()
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
