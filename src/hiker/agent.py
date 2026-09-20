"""One hiker.

A :class:`Hiker` owns a private history (the row indices of the chips it has
visited, and their embeddings), its own random generator, and the config dials.
:meth:`Hiker.step` performs exactly the six sub-steps from the brief and returns a
:class:`StepResult` for logging. The class knows nothing about files or images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .scoring import novelty_scores, rank_of, select_softmax, taste_bonus, update_taste


@dataclass
class StepResult:
    step: int
    chip_index: int
    novelty: float
    rank_among_candidates: int
    n_candidates: int
    was_random_jump: bool
    embedding_distance_from_prev: float
    history_size: int  # size *after* appending this chip
    taste_similarity: float | None = None  # cos_sim(chosen, taste) before the update; None if no taste yet
    taste_updated: bool = False
    taste_shift: float | None = None  # cos_dist(taste_before, taste_after) when updated


@dataclass
class Hiker:
    agent_id: int
    seed: int
    embeddings: np.ndarray  # (N, dim) unit vectors, shared and read-only
    knn: Any  # object with .search(query (1, dim), k) -> (sims, idx) like a FAISS index
    k_neighbours: int
    m_random: int
    j_history: int
    temperature: float
    # Taste (see scoring.py). ``taste_weight == 0`` disables it entirely and the walk is
    # identical to a taste-less hiker with the same seed.
    taste_weight: float = 0.0
    taste_alpha: float = 0.2
    taste_threshold: float = 0.9
    taste_init: str = "first"  # first | zero
    history: list[int] = field(default_factory=list)
    novelties: list[float] = field(default_factory=list)
    n_random_jumps: int = 0
    n_taste_updates: int = 0
    taste: np.ndarray = field(init=False)
    taste_initial: np.ndarray = field(init=False)
    rng: np.random.Generator = field(init=False)

    def __post_init__(self) -> None:
        # Seeding with (seed, agent_id) gives every agent an independent stream that
        # is still fully determined by the run seed.
        self.rng = np.random.default_rng([self.seed, self.agent_id])
        if self.taste_init not in ("first", "zero"):
            raise ValueError("taste_init must be 'first' or 'zero'")
        self.taste = np.zeros(self.embeddings.shape[1], dtype=np.float32)
        self.taste_initial = self.taste.copy()

    # -- state ---------------------------------------------------------------------

    @property
    def current(self) -> int:
        return self.history[-1]

    def history_matrix(self) -> np.ndarray:
        return self.embeddings[self.history]

    def start(self, chip_index: int | None = None) -> int:
        """Place the agent on its first chip (random if not given). Returns the index."""
        if chip_index is None:
            chip_index = int(self.rng.integers(0, self.embeddings.shape[0]))
        self.history = [chip_index]
        self.novelties = []
        self.n_taste_updates = 0
        if self.taste_weight != 0.0 and self.taste_init == "first":
            self.taste = self.embeddings[chip_index].astype(np.float32).copy()
        else:
            self.taste = np.zeros(self.embeddings.shape[1], dtype=np.float32)
        self.taste_initial = self.taste.copy()
        return chip_index

    @property
    def has_taste(self) -> bool:
        return bool(np.any(self.taste))

    def taste_drift(self) -> float | None:
        """Cosine distance between the current taste and the taste it started from, or None."""
        if not self.has_taste or not np.any(self.taste_initial):
            return None
        return float(1.0 - float(self.taste @ self.taste_initial))

    def running_mean(self, window: int) -> float | None:
        if not self.novelties:
            return None
        return float(np.mean(self.novelties[-window:]))

    # -- one step ----------------------------------------------------------------------

    def candidates(self) -> tuple[np.ndarray, np.ndarray]:
        """Sub-steps 1-3: k nearest neighbours + m random chips, minus the history.

        Returns ``(indices, is_random)`` aligned arrays. Neighbours come first so that
        a chip that is both a neighbour and a random draw counts as a neighbour.
        """
        q = self.embeddings[self.current][None, :]
        # +1 because the query chip is its own nearest neighbour and gets dropped.
        n_total = self.embeddings.shape[0]
        k = min(self.k_neighbours + 1, n_total)
        _, idx = self.knn.search(q, k)
        neigh = [int(i) for i in idx[0] if i >= 0]
        if self.m_random > 0:
            rand = [int(i) for i in self.rng.choice(n_total, size=min(self.m_random, n_total), replace=False)]
        else:
            rand = []
        seen = set(self.history)
        out: list[int] = []
        flags: list[bool] = []
        for i in neigh:
            if i not in seen and i not in out:
                out.append(i)
                flags.append(False)
        for i in rand:
            if i not in seen and i not in out:
                out.append(i)
                flags.append(True)
        return np.asarray(out, dtype=np.int64), np.asarray(flags, dtype=bool)

    def step(self, step_number: int) -> StepResult | None:
        """Sub-steps 4-6: score, choose, move. Returns None if no candidate remains."""
        cand, is_rand = self.candidates()
        if len(cand) == 0:
            return None
        novelty = novelty_scores(self.embeddings[cand], self.history_matrix(), self.j_history)
        if self.taste_weight != 0.0:
            scores = novelty + taste_bonus(self.embeddings[cand], self.taste, self.taste_weight)
        else:
            scores = novelty
        choice, _ = select_softmax(scores, self.temperature, self.rng)
        chosen = int(cand[choice])
        prev = self.current
        emb_dist = float(1.0 - float(self.embeddings[prev] @ self.embeddings[chosen]))
        nov = float(novelty[choice])
        self.history.append(chosen)
        self.novelties.append(nov)
        if is_rand[choice]:
            self.n_random_jumps += 1
        # Taste: similarity is measured against the taste that made the choice; then
        # the taste moves if the encounter was strong enough.
        taste_sim: float | None = None
        taste_updated = False
        taste_shift: float | None = None
        if self.taste_weight != 0.0:
            e = self.embeddings[chosen]
            if self.has_taste:
                taste_sim = float(e @ self.taste)
            if nov >= self.taste_threshold:
                before = self.taste
                self.taste = update_taste(before, e, nov, self.taste_alpha)
                taste_updated = True
                self.n_taste_updates += 1
                if np.any(before):
                    taste_shift = float(1.0 - float(before @ self.taste))
                else:
                    taste_shift = 1.0  # the first spike set the taste from nothing
                if not np.any(self.taste_initial):
                    self.taste_initial = self.taste.copy()
        return StepResult(
            step=step_number,
            chip_index=chosen,
            novelty=nov,
            rank_among_candidates=rank_of(choice, scores),
            n_candidates=int(len(cand)),
            was_random_jump=bool(is_rand[choice]),
            embedding_distance_from_prev=emb_dist,
            history_size=len(self.history),
            taste_similarity=taste_sim,
            taste_updated=taste_updated,
            taste_shift=taste_shift,
        )
