"""Task 3, part 1: how much does each character's choice follow its own score? From candidates.parquet of all h2910 runs (and h0111
runs once they exist). Steps with a real choice (more than one candidate), after the 50-step warm-up.

    python analysis/h0111/task3_rank.py

Rank 1 = the top-scored candidate. Chance of the top rank under a uniform choice is the mean of 1/C. Far tiles (Globalist question):
how often an offered far tile is taken against chance, the far tile's own probability under the softmax, and the same top-rank
measure on steps where no far tile was offered.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from common import H2910, OUT, RUNS, WARMUP, candidates


def one(run: str, ch: str, start: str, I_col: str = "I") -> tuple[dict, pd.DataFrame]:
    c = candidates(run)
    c = c[c.step >= WARMUP].copy()
    c["C"] = c.groupby("step").step.transform("size")
    c = c[c.C > 1]
    c["rank"] = c.groupby("step")[I_col].rank(ascending=False, method="first").astype(int)
    c["soft"] = np.exp(2 * (c.I - c.groupby("step").I.transform("max")))  # the softmax of the walker's scorer at temperature 0.5, also for null
    c["soft"] /= c.groupby("step").soft.transform("sum")
    ch_ = c[c.chosen]
    has_far = c.groupby("step").kind.transform(lambda k: (k == "long").any())
    near = ch_[~has_far[ch_.index]]
    far = c[c.kind == "long"]
    far_ch = far[far.chosen]
    out = {"run": run, "character": ch, "start": start, "choices": len(ch_), "top1": (ch_["rank"] == 1).mean(), "top1_chance": (1 / ch_.C).mean(), "top2": (ch_["rank"] <= 2).mean(), "top2_chance": (2 / ch_.C).mean(),
           "bottom_half": (ch_["rank"] > ch_.C / 2).mean(), "bottom_half_chance": ((ch_.C - np.ceil(ch_.C / 2)) / ch_.C).mean(), "top1_softmax_says": c.groupby("step").soft.max().mean(),
           "near_top1": (near["rank"] == 1).mean(), "near_top1_chance": (1 / near.C).mean(), "far_offers": len(far), "far_taken": len(far_ch), "far_accept": far.chosen.mean() if len(far) else np.nan,
           "far_chance": (1 / far.C).mean() if len(far) else np.nan, "far_soft": far.soft.mean() if len(far) else np.nan, "far_top1_when_offered": (far["rank"] == 1).mean() if len(far) else np.nan,
           "far_p_under_05": (far.soft < 0.05).mean() if len(far) else np.nan, "far_p_over_50": (far.soft > 0.5).mean() if len(far) else np.nan}
    r = ch_.groupby("rank").size().rename("n").reset_index().assign(run=run, character=ch)
    return out, r


def main() -> None:
    runs = dict(H2910)
    for d in sorted(RUNS.glob("h0111_*_s*")):
        if "verify" in d.name or not (d / "final.pt").exists():
            continue
        ch = d.name.split("_s")[0].removeprefix("h0111_")
        runs[d.name] = ({"reference": "Reference", "bored": "Bored", "null": "Null"}.get(ch, ch), "Paris split")
    rows, ranks = [], []
    for run, (ch, start) in runs.items():
        o, r = one(run, ch, start)
        rows.append(o)
        ranks.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task3_rank.csv", index=False)
    pd.concat(ranks).to_csv(OUT / "task3_rank_hist.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(t.drop(columns=["choices", "top2_chance", "bottom_half_chance"]).round(3).to_string(index=False))
    h = pd.concat(ranks)
    h = h[h["rank"] <= 8].pivot_table(index=["character", "run"], columns="rank", values="n", fill_value=0)
    h = h.div(h.sum(axis=1), axis=0).groupby("character").mean().round(3)
    print("\nshare of choices by rank, mean of walks\n", h.to_string())
    figure(t, pd.concat(ranks))


def figure(t: pd.DataFrame, ranks: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = [c for c in ["Null", "Reference", "Bored", "Globalist", "Localist", "Fast learner"] if c in set(ranks.character)]
    fig, axs = plt.subplots(1, len(order), figsize=(2.7 * len(order), 3.1), sharey=True)
    for ax, c in zip(np.atleast_1d(axs), order):
        h = ranks[(ranks.character == c) & (ranks["rank"] <= 9)].pivot_table(index="run", columns="rank", values="n", fill_value=0)
        h = h.div(h.sum(axis=1), axis=0)
        ax.bar(h.columns, h.mean(), color="#2a78b5", yerr=[h.mean() - h.min(), h.max() - h.mean()], error_kw={"lw": 0.8})
        chance = t[t.character == c].top1_chance.mean()
        ax.axhline(chance, color="k", lw=0.9, ls="--")
        ax.set_title(f"{c} ({len(h)} walks)", fontsize=9)
        ax.set_xlabel("rank of the chosen tile")
    np.atleast_1d(axs)[0].set_ylabel("share of choices")
    fig.suptitle("Rank under the walker's own score. Dashed: uniform choice. Bars: mean of walks, whiskers: range", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "task3_rank.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
