import numpy as np

from hiker.agent import Hiker
from hiker.index import build_index


def make_embs(n=200, d=16, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def walk(seed, n_steps=40, **kw):
    embs = make_embs()
    idx = build_index(embs)
    h = Hiker(agent_id=0, seed=seed, embeddings=embs, knn=idx, k_neighbours=10, m_random=3, j_history=5, temperature=0.1, **kw)
    h.start()
    out = []
    for s in range(1, n_steps + 1):
        r = h.step(s)
        if r is None:
            break
        out.append((r.chip_index, round(r.novelty, 6), r.was_random_jump, r.rank_among_candidates))
    return out, h


def test_same_seed_same_walk():
    a, _ = walk(7)
    b, _ = walk(7)
    assert a == b


def test_different_seed_different_walk():
    a, _ = walk(7)
    b, _ = walk(8)
    assert a != b


def test_never_revisits():
    out, h = walk(1, n_steps=150)
    assert len(h.history) == len(set(h.history))


def test_candidates_exclude_history_and_self():
    embs = make_embs()
    idx = build_index(embs)
    h = Hiker(agent_id=0, seed=0, embeddings=embs, knn=idx, k_neighbours=10, m_random=3, j_history=5, temperature=0.1)
    h.start(5)
    h.step(1)
    cand, flags = h.candidates()
    assert not set(cand.tolist()) & set(h.history)
    assert len(cand) == len(set(cand.tolist()))
    assert len(flags) == len(cand)


def test_exhaustion_returns_none():
    embs = make_embs(n=6)
    idx = build_index(embs)
    h = Hiker(agent_id=0, seed=0, embeddings=embs, knn=idx, k_neighbours=10, m_random=3, j_history=5, temperature=0.1)
    h.start(0)
    steps = 0
    while h.step(steps + 1) is not None:
        steps += 1
    assert steps == 5
    assert h.step(99) is None


def test_greedy_temperature_picks_rank_one():
    embs = make_embs()
    idx = build_index(embs)
    h = Hiker(agent_id=0, seed=0, embeddings=embs, knn=idx, k_neighbours=10, m_random=3, j_history=5, temperature=1e-6)
    h.start(0)
    for s in range(1, 20):
        r = h.step(s)
        assert r is not None and r.rank_among_candidates == 1
