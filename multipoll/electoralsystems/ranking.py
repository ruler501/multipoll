from __future__ import annotations  # noqa: T484

from typing import List, Optional, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import multipoll.models


class Ranking:
    weights: List[Optional[float]]
    indexes: List[int]

    def __init__(self, vote: multipoll.models.FullVoteBase, collapse_ties: bool = True):
        options_count = len(vote.poll.options)
        enumerated_weights: List[Tuple[int, int]] = \
            [(i, w) for i, w in enumerate(vote.weights[:options_count]) if w is not None]
        if len(enumerated_weights) == 0:
            self.weights = [None for _ in range(options_count)]
            self.indexes = list(range(options_count))
            return
        prelims = sorted(enumerated_weights, key=lambda x: x[1], reverse=not collapse_ties)
        weights: List[Optional[float]] = [None for _ in range(options_count)]
        cur: Optional[int] = prelims[0][1]
        score: float = 1
        if collapse_ties:
            for i, w in prelims:
                if w != cur:
                    score += 1
                    cur = w
                weights[i] = score
            weights = [None if x is None else (x + len(prelims) - score)  # noqa: IF100
                       for x in weights]
        else:
            for i, w in prelims:
                if w != cur:
                    score = i + 1
                    cur = w
                weights[i] = len(prelims) - score + 1
        self.weights = weights
        none_indexes = [i for i, w in enumerate(vote.weights[:options_count])
                        if w is None]
        self.indexes = [i for i, _ in prelims] + none_indexes
