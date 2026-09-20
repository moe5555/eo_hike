import numpy as np
import pytest

from hiker.agent import Hiker
from hiker.index import build_index
from hiker.scoring import taste_bonus, update_taste


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def make_embs(n=200, d=16, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def run(seed=7, n_steps=40, **kw):
    embs = make_embs()
    h = Hiker(agent_id=0, seed=seed, embeddings=embs, knn=build_index(embs), k_neighbours=10, m_random=3,
              j_history=5, temperature=0.1, **kw)
    h.start()
    out = []
    for s in range(1, n_steps + 1):
        r = h.step(s)
        if r is None:
            break
        out.append(r)
    return out, h


def test_update_taste_is_weighted_ema_and_unit_length():
    t = unit([1, 0, 0])
    e = unit([0, 1, 0])
    new = update_taste(t, e, novelty=1.0, alpha=0.5)
    assert np.isclose(np.linalg.norm(new), 1.0)
    assert np.allclose(new, unit([0.5, 0.5, 0]))
    # a weaker strike moves the taste less
    weak = update_taste(t, e, novelty=0.5, alpha=0.5)
    assert weak @ t > new @ t


def test_update_taste_from_zero_sets_it_to_the_embedding():
    e = unit([3, 4, 0])
    new = update_taste(np.zeros(3, np.float32), e, novelty=0.7, alpha=0.2)
    assert np.allclose(new, e)


def test_update_taste_rejects_bad_alpha():
    with pytest.raises(ValueError):
        update_taste(unit([1, 0]), unit([0, 1]), 1.0, 0.0)


def test_taste_bonus_is_zero_without_taste_or_weight():
    c = make_embs(5, 4)
    assert np.all(taste_bonus(c, np.zeros(4, np.float32), 0.3) == 0)
    assert np.all(taste_bonus(c, unit([1, 0, 0, 0]), 0.0) == 0)
    b = taste_bonus(c, unit([1, 0, 0, 0]), 0.3)
    assert np.allclose(b, 0.3 * c[:, 0])


def test_weight_zero_reproduces_the_tasteless_walk():
    a, _ = run(taste_weight=0.0)
    b, _ = run()
    assert [r.chip_index for r in a] == [r.chip_index for r in b]
    assert all(r.taste_similarity is None and not r.taste_updated for r in a)


def test_init_first_uses_start_chip_and_updates_on_strong_encounters():
    out, h = run(taste_weight=0.3, taste_threshold=0.5, taste_init="first")
    assert h.taste_initial @ h.embeddings[h.history[0]] > 0.999
    assert out[0].taste_similarity is not None
    updated = [r for r in out if r.taste_updated]
    assert updated and all(r.novelty >= 0.5 for r in updated)
    assert all(r.novelty < 0.5 for r in out if not r.taste_updated)
    assert h.n_taste_updates == len(updated)
    assert all(r.taste_shift is not None and 0 <= r.taste_shift <= 2 for r in updated)
    assert np.isclose(np.linalg.norm(h.taste), 1.0)


def test_init_zero_waits_for_first_spike():
    out, h = run(taste_weight=0.3, taste_threshold=0.9, taste_init="zero")
    first = next(i for i, r in enumerate(out) if r.taste_updated)
    assert all(r.taste_similarity is None for r in out[: first + 1])
    assert out[first].taste_shift == 1.0
    assert all(r.taste_similarity is not None for r in out[first + 1 :])
    assert np.allclose(h.taste_initial, h.embeddings[out[first].chip_index]) or h.n_taste_updates > 1


def test_threshold_above_everything_freezes_taste():
    out, h = run(taste_weight=0.3, taste_threshold=5.0, taste_init="first")
    assert h.n_taste_updates == 0
    assert h.taste_drift() == pytest.approx(0.0, abs=1e-6)


def test_taste_pulls_towards_taste():
    """With a large weight the chosen chips should sit closer to the taste than the
    tasteless walk's chips do to that same vector."""
    embs = make_embs()
    t = embs[0]
    def mean_sim(w):
        h = Hiker(agent_id=0, seed=3, embeddings=embs, knn=build_index(embs), k_neighbours=10, m_random=3,
                  j_history=5, temperature=0.01, taste_weight=w, taste_threshold=5.0, taste_init="first")
        h.start(0)
        for s in range(1, 30):
            h.step(s)
        return float(np.mean(embs[h.history[1:]] @ t))
    assert mean_sim(2.0) > mean_sim(0.0)


def test_bad_init_rejected():
    embs = make_embs(20, 4)
    with pytest.raises(ValueError):
        Hiker(agent_id=0, seed=0, embeddings=embs, knn=build_index(embs), k_neighbours=5, m_random=1,
              j_history=3, temperature=0.1, taste_init="nope")
