import numpy as np
import torch

from hiker.dream import novelty_torch
from hiker.scoring import novelty_scores


def unit_rows(n, d, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_novelty_torch_matches_numpy_formula():
    e = unit_rows(1, 16, 1)
    h = unit_rows(40, 16, 2)
    got = float(novelty_torch(torch.from_numpy(e), torch.from_numpy(h), 15))
    want = float(novelty_scores(e, h, 15)[0])
    assert abs(got - want) < 1e-5


def test_novelty_torch_gradient_points_away_from_history():
    """Moving along the gradient must increase the score: the guidance direction is
    'away from what has been seen'."""
    h = torch.from_numpy(unit_rows(20, 16, 3))
    e = torch.from_numpy(unit_rows(1, 16, 4)).requires_grad_(True)
    s = novelty_torch(e, h, 5)
    (g,) = torch.autograd.grad(s, e)
    e2 = e.detach() + 0.05 * g / g.norm()
    e2 = e2 / e2.norm()
    assert float(novelty_torch(e2, h, 5)) > float(s)


def test_novelty_torch_small_history_uses_all():
    e = torch.from_numpy(unit_rows(1, 8, 1))
    h = torch.from_numpy(unit_rows(3, 8, 2))
    got = float(novelty_torch(e, h, 15))
    want = float((1 - h @ e.reshape(-1)).mean())
    assert abs(got - want) < 1e-6
