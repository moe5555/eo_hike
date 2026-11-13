"""Gate A of notes/brief_landsat_v2_run.md (section 5): the clock, the time offer, the end rule, the Null, and no death.

    .venv/bin/python -m unittest tests.test_clock -v                    # unit tests (seconds)
    WALK_TESTS=1 .venv/bin/python -m unittest tests.test_clock -v       # plus short real walks (minutes; tile cache or network)

Unit tests run on the pure functions of agent/clock.py and data/landsat1_world.one_per_day. The walk tests run agent/walk.py on the
clock world and check its logs: every step shows its cell's acquisition closest to the clock, sideways moves leave the clock alone, a
time offer is the next pass, the Null draws uniformly, the end rule and the cap fire, nothing else ends a walk, and a resumed walk is
the uninterrupted walk.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import clock as CL  # noqa: E402

WALKS = os.environ.get("WALK_TESTS") == "1"
TEST_RUNS = ROOT / "runs" / "test"


class ClosestDate(unittest.TestCase):
    days = np.array([10, 20, 30])

    def test_exact_and_between(self):
        self.assertEqual(CL.closest_rank(self.days, 20), 1)
        self.assertEqual(CL.closest_rank(self.days, 16), 1)
        self.assertEqual(CL.closest_rank(self.days, 14), 0)
        self.assertEqual(CL.closest_rank(self.days, 26), 2)

    def test_tie_goes_to_the_earlier_pass(self):
        self.assertEqual(CL.closest_rank(self.days, 15), 0)
        self.assertEqual(CL.closest_rank(self.days, 25), 1)

    def test_outside_the_range(self):
        self.assertEqual(CL.closest_rank(self.days, -100), 0)
        self.assertEqual(CL.closest_rank(self.days, 1000), 2)
        self.assertEqual(CL.closest_rank(np.array([7]), 0), 0)

    def test_brute_force(self):
        rng = np.random.default_rng(0)
        for _ in range(2000):
            d = np.unique(rng.integers(0, 400, rng.integers(1, 12)))
            t = int(rng.integers(-50, 450))
            dist = np.abs(d - t)
            self.assertEqual(CL.closest_rank(d, t), int(np.flatnonzero(dist == dist.min())[0]))  # the first minimum: the earlier pass


class TimeOffer(unittest.TestCase):
    days = np.array([10, 20, 30])

    def test_strictly_after_max_of_clock_and_tile(self):
        self.assertEqual(CL.time_offer(self.days, 10, 10), 1)
        self.assertEqual(CL.time_offer(self.days, 10, 20), 2)  # the tile seen is later than the clock: after the tile
        self.assertEqual(CL.time_offer(self.days, 25, 20), 2)  # the clock is later than the tile: after the clock
        self.assertEqual(CL.time_offer(self.days, 19, 10), 1)

    def test_absent_without_a_later_pass(self):
        self.assertIsNone(CL.time_offer(self.days, 30, 30))
        self.assertIsNone(CL.time_offer(self.days, 31, 20))
        self.assertIsNone(CL.time_offer(self.days, 10, 30))
        self.assertIsNone(CL.time_offer(np.array([5]), 5, 5))

    def test_brute_force(self):
        rng = np.random.default_rng(1)
        for _ in range(2000):
            d = np.unique(rng.integers(0, 400, rng.integers(1, 12)))
            t, dc = (int(v) for v in rng.integers(0, 420, 2))
            later = np.flatnonzero(d > max(t, dc))
            self.assertEqual(CL.time_offer(d, t, dc), int(later[0]) if len(later) else None)


class Walkthrough(unittest.TestCase):
    """A hand-made world of two cells, stepped by the rules the walker uses (agent/walk.py, stack: clock)."""

    def test_sideways_wait_return(self):
        A, B = np.array([10, 30, 50]), np.array([12, 28])
        t = 10  # start at A's first acquisition
        dA = A[CL.closest_rank(A, t)]
        self.assertEqual(dA, 10)
        # sideways to B: the clock does not move, B shows its acquisition closest to 10
        dB = B[CL.closest_rank(B, t)]
        self.assertEqual((t, dB), (10, 12))
        # wait at B: the first pass after max(t, d_B) = 12 -> 28; the clock becomes 28
        r = CL.time_offer(B, t, dB)
        t, dB = int(B[r]), int(B[r])
        self.assertEqual(t, 28)
        self.assertIsNone(CL.time_offer(B, t, dB))  # B has no later pass: no time offer
        # return to A: it shows the pass closest to 28, the later one (30), not the 10 it showed before
        self.assertEqual(A[CL.closest_rank(A, t)], 30)


class OnePerDate(unittest.TestCase):
    def test_highest_level_then_product_id(self):
        from data.landsat1_world import one_per_day

        pid = np.array(["LM01_L1GS_B", "LM01_L1TP_Z", "LM01_L1GS_A", "LM01_L1GS_C", "LM01_L1TP_Y"])
        c = pd.DataFrame({"cell": [1, 1, 2, 2, 3], "day": pd.to_datetime(["1972-08-01"] * 4 + ["1972-08-02"]),
                          "level": ["L1GS", "L1TP", "L1GS", "L1GS", "L1TP"], "scene": [0, 1, 2, 3, 4]})
        out = one_per_day(c, pid).set_index("cell")
        self.assertEqual(out.loc[1, "scene"], 1)  # L1TP over L1GS on the same day
        self.assertEqual(out.loc[1, "chosen_by"], "level")
        self.assertEqual(out.loc[2, "scene"], 2)  # two L1GS: the lower product ID
        self.assertEqual(out.loc[2, "chosen_by"], "product_id")
        self.assertEqual(out.loc[3, "chosen_by"], "only")
        self.assertEqual(len(out), 3)

    def test_the_built_world(self):
        d = ROOT / "data" / "landsat1" / "clock"
        if not (d / "day.npy").exists():
            self.skipTest("clock world not built (data/landsat1_world.py clock)")
        start, day = np.load(d / "start.npy"), np.load(d / "day.npy")
        cell = np.repeat(np.arange(len(start) - 1), np.diff(start))
        same = cell[1:] == cell[:-1]
        self.assertTrue((np.diff(day)[same] > 0).all(), "two products of one cell on one date, or dates out of order")
        self.assertTrue((np.diff(start) > 0).all())


class StoreSettings(unittest.TestCase):
    def test_the_gdal_settings_open(self):
        import rasterio

        from data.landsat1_store import GDAL_ENV

        with rasterio.Env(**GDAL_ENV):  # a bad value (GDAL_CACHEMAX as a string) fails here, as it failed every read of the dry run
            pass


class Calibration(unittest.TestCase):
    def test_null_rescaling_is_nan_not_an_error(self):
        from data.landsat1_store import mtl_number, toa

        self.assertTrue(np.isnan(mtl_number("NULL")) and np.isnan(mtl_number(None)))
        self.assertEqual(mtl_number("1.3602E-03"), 1.3602e-3)
        self.assertTrue(np.isnan(toa(np.full((2, 2), 19, np.uint8), mtl_number("NULL"), mtl_number("NULL"), 43.0)).all())


class EndRule(unittest.TestCase):
    def test_time_and_cap(self):
        self.assertEqual(CL.end_reason(100, 5, 100, 50), "time")
        self.assertEqual(CL.end_reason(101, 5, 100, 50), "time")
        self.assertIsNone(CL.end_reason(99, 49, 100, 50))
        self.assertEqual(CL.end_reason(99, 50, 100, 50), "capped")
        self.assertEqual(CL.end_reason(100, 50, 100, 50), "time")  # the clock wins a tie with the cap

    def test_linger(self):
        self.assertIsNone(CL.end_reason(99, 10, 100, 50))  # off unless set
        self.assertEqual(CL.end_reason(99, 30, 100, 50, linger_end=30), "linger")
        self.assertIsNone(CL.end_reason(99, 29, 100, 50, linger_end=30))
        self.assertEqual(CL.end_reason(100, 30, 100, 50, linger_end=30), "time")  # the clock's end wins

    def test_tile_cap(self):
        self.assertIsNone(CL.end_reason(99, 10, 100, 50, 10**6))  # off unless set
        self.assertEqual(CL.end_reason(99, 10, 100, 50, 20000, 20000), "tiles")
        self.assertIsNone(CL.end_reason(99, 10, 100, 50, 19999, 20000))
        self.assertEqual(CL.end_reason(100, 10, 100, 50, 20000, 20000), "time")

    def test_nothing_else_ends_a_walk(self):
        rng = np.random.default_rng(2)
        for _ in range(5000):
            t, s, te, cap = (int(v) for v in rng.integers(0, 1000, 4))
            self.assertIn(CL.end_reason(t, s, te, cap), (None, *CL.END_REASONS))


class NullDraw(unittest.TestCase):
    def test_uniform_over_the_offers(self):
        for C in range(1, 10):
            I = np.random.default_rng(C).normal(size=C) * 10
            np.testing.assert_array_equal(CL.choice_probs(I, 0.5, True), np.full(C, 1.0 / C))

    def test_draws_are_uniform(self):
        rng = np.random.default_rng(3)
        C, n = 9, 90000
        I = np.array([5.0, -3, 0, 0, 1, 2, -8, 4, 9])  # interest must not matter
        x = np.bincount([rng.choice(C, p=CL.choice_probs(I, 0.5, True)) for _ in range(n)], minlength=C)
        chi2 = float((((x - n / C) ** 2) / (n / C)).sum())
        self.assertLess(chi2, 26.1)  # p = 0.001 at 8 degrees of freedom

    def test_softmax_is_walk_pys(self):
        I = np.array([0.3, -1.2, 2.0])
        logits = I / 0.5
        p = np.exp(logits - logits.max())
        p /= p.sum()
        np.testing.assert_array_equal(CL.choice_probs(I, 0.5, False), p)


class NoDeath(unittest.TestCase):
    def test_the_walk_loop_breaks_only_on_the_end_rule(self):
        src = (ROOT / "agent" / "walk.py").read_text()
        run = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "run")
        loop = next(n for n in ast.walk(run) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "step")
        breaks = [n for n in ast.walk(loop) if isinstance(n, ast.Break)]
        self.assertEqual(len(breaks), 1, "the step loop has a break other than the end rule's")
        returns = [n for n in ast.walk(loop) if isinstance(n, ast.Return)]
        self.assertEqual(len(returns), 1, "the step loop returns other than through stop_after")  # the test hook, after a checkpoint
        code = ast.unparse(loop)  # the code without its comments
        self.assertIn("end_reason = CL.end_reason(clk, s1, t_end, cap, len(set(te.tiles)), tile_cap, linger_end)", code)
        for word in ("death", "die(", "kill", "sys.exit", "exit("):
            self.assertNotIn(word, code.lower())


# -- walks -------------------------------------------------------------------------------------------------------------------
def walk(cond: str, name: str, steps: int, extra: dict | None = None, args: tuple = ()) -> Path:
    cfg = yaml.safe_load((ROOT / "configs" / "gen1" / f"{cond}.yaml").read_text())
    cfg.update({"condition": name, "ckpt_every": 20, "render_every": 10, "reembed_every": 20, **(extra or {})})
    cdir = TEST_RUNS / "configs"
    cdir.mkdir(parents=True, exist_ok=True)
    p = cdir / f"{name}.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))
    env = {**os.environ, "OMP_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
    subprocess.run([sys.executable, "-m", "agent.walk", str(p), "--walk", "1", "--phase", "test", "--steps", str(steps), *args],
                   cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    return TEST_RUNS / name / "w001"


@unittest.skipUnless(WALKS, "WALK_TESTS=1 runs short real walks")
class Walks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from data.landsat1_store import Landsat1ClockStore

        cls.store = Landsat1ClockStore()
        cls.cur = walk("curious", "t_curious", 60)
        cls.null = walk("null", "t_null", 60)

    def logs(self, run: Path):
        return pd.read_parquet(run / "steps.parquet"), pd.read_parquet(run / "candidates.parquet"), json.loads((run / "walk.json").read_text())

    def test_every_tile_is_its_cells_acquisition_closest_to_the_clock(self):
        for run in (self.cur, self.null):
            s, c, _ = self.logs(run)
            for r in s.itertuples():
                self.assertEqual(r.acq_rank, CL.closest_rank(self.store.days(r.tile_idx), r.clock_day), f"{run.name} step {r.step}")
            # every compass offer too, at the clock of its step (returns included)
            o = c[c.kind == "compass"]
            for r in o.itertuples():
                self.assertEqual(r.acq_rank, CL.closest_rank(self.store.days(r.tile_idx), r.clock_day))

    def test_sideways_moves_never_change_the_clock(self):
        for run in (self.cur, self.null):
            s, _, _ = self.logs(run)
            side = s[s.offer_kind != "time"]
            self.assertTrue((side.clock == side.clock_before).all())
            self.assertTrue(side.wait_days.isna().all())

    def test_a_wait_is_the_next_pass(self):
        for run in (self.cur, self.null):
            s, c, _ = self.logs(run)
            w = s[s.offer_kind == "time"]
            self.assertGreater(len(w) + (c.kind == "time").sum(), 0, "no time offer in 60 steps")
            for r in w.itertuples():
                prev = s.iloc[r.step - 1] if r.step else None
                d = self.store.days(r.tile_idx)
                d_c = prev.tile_day if prev is not None else d[0]
                t = prev.clock_day if prev is not None else d[0]
                self.assertEqual(int(d[CL.time_offer(d, t, d_c)]), r.clock_day)
                self.assertGreater(r.clock_day, max(t, d_c))
                self.assertEqual(r.tile_idx, prev.tile_idx if prev is not None else r.tile_idx)  # the wanderer stays on its cell
            # a time offer exists exactly when the current cell has a later pass
            for r in s.itertuples():
                prev = s.iloc[r.step - 1] if r.step else None
                if prev is None:
                    continue
                d = self.store.days(prev.tile_idx)
                self.assertEqual(r.time_exists, CL.time_offer(d, prev.clock_day, prev.tile_day) is not None, f"step {r.step}")
                self.assertEqual(r.time_offered, r.time_exists)  # time_offer_p 1: nothing thinned

    def test_the_null_draws_uniformly(self):
        _, c, _ = self.logs(self.null)
        n = c.groupby("step").size()
        np.testing.assert_allclose(c.p.to_numpy(), 1.0 / n.reindex(c.step).to_numpy())
        _, cc, _ = self.logs(self.cur)
        self.assertFalse(np.allclose(cc.p.to_numpy(), 1.0 / cc.groupby("step").size().reindex(cc.step).to_numpy()))

    def test_the_cap_fires(self):
        for run in (self.cur, self.null):
            s, _, w = self.logs(run)
            self.assertEqual((w["end_reason"], w["steps"], len(s)), ("capped", 60, 60))

    def test_the_end_rule_fires_at_t_end(self):
        s0, _, _ = self.logs(self.cur)
        waits = s0[s0.offer_kind == "time"]
        if not len(waits):
            self.skipTest("no wait in the curious walk")
        first = waits.iloc[0]
        run = walk("curious", "t_end", 60, {"t_end": first.clock})  # the same walk, with T_end at its first wait's date
        s, _, w = self.logs(run)
        self.assertEqual(w["end_reason"], "time")
        self.assertEqual(len(s), int(first.step) + 1, "the walk must end at the first step where the clock reaches T_end")
        self.assertTrue((s.clock_day.iloc[:-1] < CL.to_day(first.clock)).all())

    def test_resume_is_the_uninterrupted_walk(self):
        part = walk("curious", "t_resume", 60, args=("--stop-after", "40"))
        self.assertTrue((part / "resume.pt").exists() and not (part / "walk.json").exists())
        walk("curious", "t_resume", 60, args=("--resume",))
        a, ca, _ = self.logs(self.cur)
        b, cb, wb = self.logs(part)
        self.assertEqual(wb["steps"], 60)
        cols = ["tile_idx", "image_key", "offer_kind", "clock_day", "tile_day", "r_km", "e", "n", "g", "I", "p_chosen", "n_glance", "err_after"]
        if (a.n_dropped.sum() + b.n_dropped.sum()) == 0:  # an offer dropped on a fetch timeout changes the walk: compare only without
            pd.testing.assert_frame_equal(a[cols], b[cols])
            np.testing.assert_array_equal(ca.I.to_numpy(), cb.I.to_numpy())
        else:
            self.skipTest("an offer was dropped on a fetch timeout")



@unittest.skipUnless(WALKS, "WALK_TESTS=1 runs short real walks")
class ThinnedWalk(unittest.TestCase):
    """The thinned time offer (Moe 2026-11-13): offered only where a later pass exists, and then with probability time_offer_p."""

    def test_thinning(self):
        run = walk("null", "t_thin", 120, {"time_offer_p": 0.5})
        s = pd.read_parquet(run / "steps.parquet")
        self.assertFalse((s.time_offered & ~s.time_exists).any(), "a time offer where no later pass exists")
        n = int(s.time_exists.sum())
        self.assertGreater(n, 10, "too few steps with a later pass to test")
        k = int(s.time_offered.sum())
        self.assertLess(abs(k - 0.5 * n), 3.3 * (0.25 * n) ** 0.5, f"{k} of {n} offered at p 0.5")
        self.assertTrue((s.offer_kind[~s.time_offered] != "time").all())


if __name__ == "__main__":
    unittest.main()
