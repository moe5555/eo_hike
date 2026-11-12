"""The forgetting check's fixed tiles (notes/brief_landsat_pipeline.md, C10): ordinary sea, sand and field, 8 each.

    python analysis/e12/forget_set.py pass      # from the e10 pass world (sqrt) -> configs/12_two_eye/forget_pass.csv
    python analysis/e12/forget_set.py mission   # from the mission world's baseline cells -> configs/12_two_eye/forget_mission.csv

Chosen from the rendered tiles (the one view) and the quirk table, never shown to the walker. Ordinary means: QA cloud below 1 %,
fill below 1 %, every band's stripe share below 1 %, nothing at DN 255, sun above 20 degrees. Then
    sea   the cover class is ocean (pass) or coast (mission: the world holds no open ocean), and the tile is dark in nir (mean R < 60);
    sand  land, the brightest quarter, and nir about red (|R - G| / (R + G) < 0.05 in the CIR tile);
    field land, mean pixel above 40 (not dark), the top quarter of (R - G) / (R + G) in the CIR tile (red = nir).
8 of each drawn with seed 0. Hand-set thresholds; the set only has to be ordinary and fixed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "configs" / "12_two_eye"


def pick(stats: pd.DataFrame, sea_cover: str) -> pd.DataFrame:
    s = stats
    ok = (s.cloud < 0.01) & (s.fill < 0.01) & (s.stripe_max < 0.01) & (s.at255_max == 0) & (s.sun_elevation > 20)
    s = s[ok]
    nd = (s.R - s.G) / (s.R + s.G + 1e-6)
    br = s[["R", "G", "B"]].mean(axis=1)
    rng = np.random.default_rng(0)
    sets = {"sea": s[(s.cover == sea_cover) & (s.R < 60)],
            "sand": s[(s.cover == "land") & (br >= br[s.cover == "land"].quantile(0.75)) & (nd.abs() < 0.05)],
            "field": s[(s.cover == "land") & (br > 40) & (nd >= nd[(s.cover == "land") & (br > 40)].quantile(0.75))]}
    out = []
    for k, d in sets.items():
        assert len(d) >= 8, f"{k}: only {len(d)} candidates"
        out.append(pd.DataFrame({"tile_idx": np.sort(rng.choice(d.tile_idx.to_numpy(), 8, replace=False)), "kind": k}))
    return pd.concat(out, ignore_index=True)


def main(which: str) -> None:
    from data import landsat1_store as L

    if which == "pass":
        from data.landsat_pass import PassStore

        st = PassStore("data/landsat/LM01_183_19721122/c10680m_256px_cir_sqrt")
        q = st.quirks(range(st.N)).set_index("tile_idx")
        means = np.stack([np.asarray(st.tiles[i]).reshape(-1, 3).mean(0) for i in range(st.N)])
        idx = st.idx.set_index("idx")
        s = q.join(idx[["cover", "sun_elevation"]])
    else:
        st = L.Landsat1TileStore()
        q = st.quirks(st.cached_ids()).set_index("tile_idx")
        means = np.stack([st.get_lowres(i).reshape(-1, 3).mean(0) for i in q.index])
        s = q.join(st.idx[["cover"]])
    s["R"], s["G"], s["B"] = means[:, 0], means[:, 1], means[:, 2]
    s["stripe_max"] = s[[f"stripe_{b}" for b in L.BANDS]].max(axis=1)
    s["at255_max"] = s[[f"at255_{b}" for b in L.BANDS]].max(axis=1)
    f = pick(s.reset_index(), "ocean" if which == "pass" else "coast")
    OUT.mkdir(parents=True, exist_ok=True)
    f.to_csv(OUT / f"forget_{which}.csv", index=False)
    print(f.groupby("kind").tile_idx.apply(list))


if __name__ == "__main__":
    main(sys.argv[1])
