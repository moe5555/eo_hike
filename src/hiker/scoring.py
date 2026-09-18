"""Novelty scoring and softmax selection. Pure numpy, no I/O, unit tested.

Notation
--------
All embeddings are unit vectors (L2-normalised), so for two chips ``a`` and ``b``

    cos_sim(a, b)  = a . b            in [-1, 1]
    cos_dist(a, b) = 1 - a . b        in [0, 2]

Novelty of a candidate ``c`` against an agent's history ``H = {h_1 .. h_n}``
(Lehman & Stanley 2008, "sparseness"):

    novelty(c, H) = (1 / j') * sum_{i in NN_j'(c, H)} cos_dist(c, h_i)

where ``NN_j'(c, H)`` are the ``j' = min(j, n)`` history entries closest to ``c``.
It is the average distance to the *nearest* things already seen: a chip that
resembles even a few past chips scores low, however different it is from the rest.
That is what makes novelty a property of the whole walk rather than of the last step.

Selection is a softmax over candidate scores with temperature ``T``:

    p_i = exp(s_i / T) / sum_k exp(s_k / T)

``T -> 0`` picks the argmax (greedy); large ``T`` approaches uniform choice.
"""

from __future__ import annotations

import numpy as np


def cosine_distances(candidates: np.ndarray, history: np.ndarray) -> np.ndarray:
    """Pairwise cosine distances ``1 - C @ H.T`` between unit rows. Shape ``(c, h)``.

    Inputs must already be L2-normalised; this function does not re-normalise so the
    score stays identical to what the FAISS inner-product index sees.
    """
    c = np.asarray(candidates, dtype=np.float32)
    h = np.asarray(history, dtype=np.float32)
    if c.ndim != 2 or h.ndim != 2:
        raise ValueError("candidates and history must be 2-D (n, dim) arrays")
    sims = c @ h.T
    return 1.0 - sims


def novelty_scores(candidates: np.ndarray, history: np.ndarray, j: int) -> np.ndarray:
    """Mean cosine distance from each candidate to its ``j`` nearest history entries.

    Args:
        candidates: ``(c, dim)`` unit vectors.
        history: ``(n, dim)`` unit vectors already visited by this agent. ``n >= 1``.
        j: how many nearest history entries to average over. If ``n < j`` all are used.

    Returns:
        ``(c,)`` float64 array of scores in ``[0, 2]``.
    """
    if j < 1:
        raise ValueError("j must be >= 1")
    if history.shape[0] == 0:
        raise ValueError("history must contain at least one entry")
    d = cosine_distances(candidates, history).astype(np.float64)
    jj = min(j, d.shape[1])
    if jj == d.shape[1]:
        nearest = d
    else:
        # np.partition puts the jj smallest in the first jj slots (unordered), which
        # is all we need for a mean and is O(h) instead of O(h log h).
        nearest = np.partition(d, jj - 1, axis=1)[:, :jj]
    return nearest.mean(axis=1)


def softmax(scores: np.ndarray, temperature: float) -> np.ndarray:
    """Numerically stable softmax of ``scores / temperature``.

    ``temperature`` must be > 0. Subtracting the max before exponentiating does not
    change the result but prevents overflow for small temperatures.
    """
    if temperature <= 0:
        raise ValueError("temperature must be > 0 (use a tiny value for near-greedy)")
    s = np.asarray(scores, dtype=np.float64) / temperature
    s = s - s.max()
    e = np.exp(s)
    return e / e.sum()


def select_softmax(scores: np.ndarray, temperature: float, rng: np.random.Generator) -> tuple[int, np.ndarray]:
    """Sample one index in proportion to ``softmax(scores / T)``.

    Returns ``(chosen_index, probabilities)``. Uses ``rng`` only, so the choice is
    reproducible from the agent's seed.
    """
    p = softmax(scores, temperature)
    idx = int(rng.choice(len(p), p=p))
    return idx, p


def rank_of(index: int, scores: np.ndarray) -> int:
    """1-based rank of ``scores[index]`` among ``scores``, highest score = rank 1.

    Ties are broken by position so the rank is deterministic.
    """
    order = np.lexsort((np.arange(len(scores)), -np.asarray(scores, dtype=np.float64)))
    return int(np.where(order == index)[0][0]) + 1
