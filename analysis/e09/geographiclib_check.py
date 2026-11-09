"""Stage 0.2: agent.compass.destination() against geographiclib on a sphere of the same radius. Needs only numpy and geographiclib, so it
runs in a throwaway environment and the project gains no dependency:

    python analysis/e09/geometry.py --export
    uv run --no-project --with geographiclib --with numpy python analysis/e09/geographiclib_check.py
"""

from pathlib import Path

import numpy as np
from geographiclib.geodesic import Geodesic

f = np.load(Path(__file__).resolve().parents[2] / "data" / "sheet" / "e09_geometry_cases.npz")
G = Geodesic(float(f["R"]) * 1000.0, 0.0)  # a sphere: flattening 0
err_m, err_lon = [], []
for la, lo, b, d, la2, lo2 in zip(f["lat"], f["lon"], f["b"], f["d"], f["la2"], f["lo2"]):
    g = G.Direct(float(la), float(lo), float(b), float(d) * 1000.0)
    inv = G.Inverse(g["lat2"], g["lon2"], float(la2), float(lo2))
    err_m.append(inv["s12"])
print(f"geographiclib (sphere R = {float(f['R'])} km): {len(err_m)} cases, max position difference {max(err_m):.3g} m, median {np.median(err_m):.3g} m")
