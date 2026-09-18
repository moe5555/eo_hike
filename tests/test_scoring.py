import numpy as np
import pytest

from hiker.scoring import cosine_distances, novelty_scores, rank_of, select_softmax, softmax


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def test_cosine_distance_basic():
    a = unit([[1, 0], [0, 1], [-1, 0]])
    h = unit([[1, 0]])
    d = cosine_distances(a, h)[:, 0]
    assert d == pytest.approx([0.0, 1.0, 2.0], abs=1e-6)


def test_novelty_is_mean_of_j_nearest():
    # history: three unit vectors at 0, 60 and 180 degrees from candidate (1, 0)
    cand = unit([[1, 0]])
    hist = unit([[1, 0], [np.cos(np.pi / 3), np.sin(np.pi / 3)], [-1, 0]])
    # distances: 0, 0.5, 2
    assert novelty_scores(cand, hist, j=1)[0] == pytest.approx(0.0, abs=1e-6)
    assert novelty_scores(cand, hist, j=2)[0] == pytest.approx(0.25, abs=1e-6)
    assert novelty_scores(cand, hist, j=3)[0] == pytest.approx(2.5 / 3, abs=1e-6)
    # j larger than history uses everything
    assert novelty_scores(cand, hist, j=50)[0] == pytest.approx(2.5 / 3, abs=1e-6)


def test_novelty_uses_own_history_not_previous_only():
    # A candidate identical to something seen long ago must score ~0 even if it is
    # far from the most recent chip.
    cand = unit([[1, 0]])
    hist = unit([[1, 0], [0, 1], [0, 1], [0, 1]])  # first entry is the twin
    assert novelty_scores(cand, hist, j=1)[0] == pytest.approx(0.0, abs=1e-6)


def test_novelty_shape_and_range():
    rng = np.random.default_rng(0)
    cand = unit(rng.normal(size=(20, 8)))
    hist = unit(rng.normal(size=(7, 8)))
    s = novelty_scores(cand, hist, j=3)
    assert s.shape == (20,)
    assert np.all(s >= 0) and np.all(s <= 2)


def test_novelty_rejects_empty_history():
    with pytest.raises(ValueError):
        novelty_scores(unit([[1, 0]]), np.zeros((0, 2), dtype=np.float32), j=1)


def test_softmax_sums_to_one_and_is_stable():
    p = softmax(np.array([1000.0, 999.0]), temperature=0.001)
    assert p.sum() == pytest.approx(1.0)
    assert p[0] > 0.99


def test_softmax_temperature_limits():
    s = np.array([0.1, 0.5, 0.3])
    greedy = softmax(s, temperature=1e-4)
    assert np.argmax(greedy) == 1 and greedy[1] > 0.999
    hot = softmax(s, temperature=100.0)
    assert np.allclose(hot, 1 / 3, atol=1e-3)


def test_softmax_rejects_bad_temperature():
    with pytest.raises(ValueError):
        softmax(np.array([0.1, 0.2]), temperature=0.0)


def test_select_softmax_is_reproducible_and_follows_probabilities():
    s = np.array([0.0, 1.0, 0.0])
    picks_a = [select_softmax(s, 0.5, np.random.default_rng(3))[0] for _ in range(1)]
    picks_b = [select_softmax(s, 0.5, np.random.default_rng(3))[0] for _ in range(1)]
    assert picks_a == picks_b
    rng = np.random.default_rng(0)
    picks = np.array([select_softmax(s, 0.5, rng)[0] for _ in range(2000)])
    p = softmax(s, 0.5)
    assert abs((picks == 1).mean() - p[1]) < 0.03


def test_rank_of():
    s = np.array([0.2, 0.9, 0.5, 0.9])
    assert rank_of(1, s) == 1
    assert rank_of(3, s) == 2  # tie broken by position
    assert rank_of(2, s) == 3
    assert rank_of(0, s) == 4
