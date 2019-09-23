from __future__ import annotations  # noqa: T484

from typing import Iterable, List, Optional, Tuple, TypeVar

import multipoll.models

Numeric = TypeVar('Numeric')


class Ranking:
    def __init__(self, vote: multipoll.models.FullVoteBase[Numeric], collapse_ties: bool = True):
        options_count = len(vote.poll.options)
        enumerated_weights: Iterable[Tuple[int, Optional[Numeric]]] = \
            enumerate(vote.weights[:options_count])
        prelims = sorted(enumerated_weights, key=lambda x: x[1] or 0, reverse=not collapse_ties)
        weights: List[Optional[float]] = [None for _ in prelims]
        cur: Optional[Numeric] = prelims[0][1]
        score: float = 1
        if collapse_ties:
            for i, w in prelims:
                if w is None:
                    weights[i] = None
                else:
                    if w != cur:
                        score += 1
                        cur = w
                    weights[i] = score
            weights = [None if x is None else (x + len(prelims) - score) for x in weights]
        else:
            for i, w in prelims:
                if w is None:
                    weights[i] = None
                else:
                    if w != cur:
                        score = i + 1
                        cur = w
                    weights[i] = len(prelims) - score + 1
        self.weights = weights
        self.indexes = [i for i, _ in prelims]