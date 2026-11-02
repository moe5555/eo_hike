"""Task 5: why about a quarter of steps go straight back (A→B→A).

    python analysis/h0111/task5_backsteps.py

Every step at which the tile left two steps ago (A) is on offer again, returned to or not. A's error on the scoring crops is compared
over time: at arrival (`e` when chosen), just after training on it (`e_self_after`, instrumented h0111 runs only), and at the moment it is
offered again, after training on B. Interference: A got harder to draw because of B. Rescaling artefact: A's score is above the running
~50-step baseline (I > 0) while its raw novelty and progress, on a yardstick fixed over the whole walk (I_abs), are not high. Chance: the
share of returns a uniform choice among the same options would have produced.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from common import H2910, OUT, RUNS, WARMUP, candidates, steps


def table(run: str) -> pd.DataFrame:
    s, c = steps(run), candidates(run)
    t = s.tile_idx.to_numpy()
    first = s.drop_duplicates("tile_idx").set_index("tile_idx").e
    c = c[c.step >= WARMUP].copy()
    c["C"] = c.groupby("step").step.transform("size")
    c["rank"] = c.groupby("step").I.rank(ascending=False, method="first")
    c["soft"] = np.exp(2 * (c.I - c.groupby("step").I.transform("max")))  # temperature 0.5, also for null (which logs a uniform p)
    c["soft"] /= c.groupby("step").soft.transform("sum")
    nb = c[c.kind == "neighbour"]
    mn, sn, mg, sg = nb.n.mean(), nb.n.std(), nb.g.mean(), nb.g.std()  # the whole walk's yardstick, not the last ~50 steps
    c["I_abs"] = (c.n - mn) / sn + (c.g - mg) / sg
    c["pct_n"], c["pct_g"] = np.searchsorted(np.sort(nb.n), c.n) / len(nb), np.searchsorted(np.sort(nb.g), c.g) / len(nb)
    a = c[(c.kind == "neighbour") & (c.step >= WARMUP + 2)]
    a = a[a.tile_idx.to_numpy() == t[a.step.to_numpy() - 2]].copy()
    i = a.step.to_numpy() - 2
    a["e_at_arrival"] = s.e.to_numpy()[i]
    a["e_first_ever"] = first.reindex(a.tile_idx).to_numpy()
    a["I_at_arrival"] = s.I.to_numpy()[i]
    a["prior_visits"] = [(t[: st] == x).sum() for st, x in zip(a.step.to_numpy(), a.tile_idx.to_numpy())]
    others = c[c.groupby("step").kind.transform("size") > 1].groupby("step")[["n_z", "g_z"]].mean()
    a["lead_n_z"] = a.n_z - others.n_z.reindex(a.step).to_numpy()
    a["lead_g_z"] = a.g_z - others.g_z.reindex(a.step).to_numpy()
    if "e_self_after" in s:
        a["e_after_training"] = s.e_self_after.to_numpy()[i]
        a["e_after_b_check"] = s.e_prev_after.to_numpy()[i + 1]
    return a.assign(run=run)


def summarise(a: pd.DataFrame, s: pd.DataFrame) -> dict:
    t = s.tile_idx.to_numpy()
    back = a[a.chosen]
    o = {"back_share": float(np.mean(t[2:] == t[:-2])), "offered": len(a), "returned": len(back), "return_rate": a.chosen.mean(), "chance_rate": (1 / a.C).mean(), "soft_rate": a.soft.mean(),
         "chance_share_of_returns": (1 / a.C).sum() / a.soft.sum(),
         # did the error rise?
         "ret_above_arrival": (back.e > back.e_at_arrival).mean(), "ret_above_first": (back.e > back.e_first_ever).mean(), "no_ret_above_arrival": (a[~a.chosen].e > a[~a.chosen].e_at_arrival).mean(),
         "ret_e_ratio_arrival": (back.e / back.e_at_arrival).median(), "no_ret_e_ratio_arrival": (a[~a.chosen].e / a[~a.chosen].e_at_arrival).median(),
         # high in absolute terms or only against the recent baseline?
         "real": ((back.I > 0) & (back.I_abs > 0)).mean(), "artefact": ((back.I > 0) & (back.I_abs <= 0)).mean(), "low_score": (back.I <= 0).mean(), "abs_only": ((back.I <= 0) & (back.I_abs > 0)).mean(),
         "pct_n": back.pct_n.median(), "pct_g": back.pct_g.median(), "top_rank": (back["rank"] == 1).mean(), "lead_n_z": back.lead_n_z.mean(), "lead_g_z": back.lead_g_z.mean(), "first_return": (back.prior_visits == 1).mean(),
         "no_ret_real": ((a[~a.chosen].I > 0) & (a[~a.chosen].I_abs > 0)).mean(), "no_ret_top": (a[~a.chosen]["rank"] == 1).mean(), "I_drop": (back.I - back.I_at_arrival).median()}
    if "e_after_training" in a:
        for lab, d in (("ret", back), ("no_ret", a[~a.chosen])):
            gain = d.e_at_arrival - d.e_after_training
            o[f"{lab}_rose_since_training"] = (d.e > d.e_after_training).mean()
            o[f"{lab}_rise_ratio"] = (d.e / d.e_after_training).median()
            o[f"{lab}_lost_half_gain"] = (((d.e - d.e_after_training) > 0.5 * gain) & (gain > 0)).mean()
            o[f"{lab}_above_arrival_again"] = (d.e > d.e_at_arrival).mean()
        d = a.assign(rise=a.e / a.e_after_training)
        q = d.groupby(pd.qcut(d.rise, 4, labels=["q1", "q2", "q3", "q4"]), observed=True).chosen.mean()
        o |= {f"return_rate_rise_{k}": v for k, v in q.items()}
        o["check_e_prev_equals_e"] = float(np.abs(a.e - a.e_after_b_check).max())
    return o


def main() -> None:
    runs = {r: (c, st) for r, (c, st) in H2910.items() if r not in {"h2910_fastlearner_s1"}}
    for d in sorted(RUNS.glob("h0111_*_s*")):
        name = d.name.split("_s")[0].removeprefix("h0111_")
        if name in ("reference", "null", "bored") and (d / "final.pt").exists():
            runs[d.name] = ({"reference": "Reference", "null": "Null", "bored": "Bored"}[name], "Paris split")
    rows = []
    for run, (ch, st) in runs.items():
        rows.append({"run": run, "character": ch, "start": st, **summarise(table(run), steps(run))})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task5_backsteps.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 60, "display.max_rows", 100):
        print(t.set_index(["run"]).drop(columns=["character", "start"]).T.round(3).to_string())


if __name__ == "__main__":
    main()
