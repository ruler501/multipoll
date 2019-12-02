from __future__ import annotations  # noqa: T484

from typing import List, Optional, Tuple, Union


class InfinityType:
    pass


INFINITY = InfinityType()


def normalize_scores(scores: List[Optional[Union[float, int]]],
                     dim: Union[int, InfinityType] = 2) -> List[Optional[float]]:
    enumerated_weights: List[Tuple[int, Union[float, int]]] = \
        [(i, w) for i, w in enumerate(scores) if w is not None]
    if len(enumerated_weights) == 0:
        return [None for _ in scores]
    if isinstance(dim, InfinityType):
        norm = max(abs(w) for _, w in enumerated_weights)
    elif dim == 0:
        norm = len([i for i, w in enumerated_weights if w != 0])
    else:
        norm = sum(abs(w) ** dim for _, w in enumerated_weights) ** (1 / dim)
    norm = abs(norm)
    if norm == 0:
        enumerated_scores = [(i, 0.0) for i, _ in enumerated_weights]
    else:
        enumerated_scores = [(i, len(scores) * w / norm) for i, w in enumerated_weights]
    scores = [None for _ in scores]
    for i, w in enumerated_scores:
        scores[i] = w
    return scores


def normalize_scores_with_fixed_max_ints(scores: List[Optional[Union[float, int]]],
                                         max_score: Optional[int] = None) -> List[Optional[int]]:
    if max_score is None:
        max_score = len(scores)
    scaling_factor = max_score / max(s for s in scores if s is not None)
    return [None if s is None else int(s * scaling_factor) for s in scores]  # noqa: IF100