from typing import Iterable, Tuple, List

from multipoll.models import FullVote
from multipoll.utils import OptNumeric


class Ranking:
    def __init__(self, vote: FullVote, collapse_ties: bool = True):
        enumerated_weights: Iterable[Tuple[int, OptNumeric]] = enumerate(vote.weights)
        prelims = sorted(enumerated_weights, key=lambda x: x[1] or 0, reverse=not collapse_ties)
        weights: List[OptNumeric] = [None for _ in prelims]
        cur: OptNumeric = prelims[0][1]
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