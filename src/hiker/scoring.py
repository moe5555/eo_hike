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


# --- taste ---------------------------------------------------------------------------
#
# A *taste vector* is an exponential moving average of the embeddings of the chips
# that struck the agent hardest. It is updated only on a *strong encounter* (novelty
# of the chosen chip >= ``threshold``) and the update is weighted by that novelty:
#
#     taste <- normalise( (1 - alpha) * taste + alpha * novelty * e )
#
# where ``e`` is the chosen chip's unit embedding. A zero taste (nothing has struck
# yet) becomes ``e`` on the first strong encounter, so "initialise as zeros and let
# the first spike set it" needs no special case. Taste enters selection as a bonus:
#
#     score(c) = novelty(c, H) + weight * cos_sim(c, taste)
#
# so the agent is pulled towards things that resemble what struck it, while novelty
# keeps pushing it away from what it has actually seen.


def taste_bonus(candidates: np.ndarray, taste: np.ndarray, weight: float) -> np.ndarray:
    """``weight * cos_sim(candidate, taste)`` per candidate; all zeros if taste is zero."""
    c = np.asarray(candidates, dtype=np.float32)
    t = np.asarray(taste, dtype=np.float32)
    if weight == 0.0 or not np.any(t):
        return np.zeros(c.shape[0], dtype=np.float64)
    return weight * (c @ t).astype(np.float64)


def update_taste(taste: np.ndarray, embedding: np.ndarray, novelty: float, alpha: float) -> np.ndarray:
    """One EMA step towards ``embedding`` with rate ``alpha * novelty``, renormalised.

    Returns a new unit vector (or the zero vector if both inputs are zero).
    """
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    t = np.asarray(taste, dtype=np.float32)
    e = np.asarray(embedding, dtype=np.float32)
    new = (1.0 - alpha) * t + alpha * float(novelty) * e
    n = float(np.linalg.norm(new))
    if n == 0.0:
        return np.zeros_like(t)
    return (new / n).astype(np.float32)
