from __future__ import annotations  # noqa

import abc
import statistics
from typing import Iterable, List
from typing import TYPE_CHECKING

from multipoll.electoralsystems.utils import electoral_system
from multipoll.electoralsystems.utils.cardinalscores import normalize_scores, \
    normalize_scores_with_fixed_max_ints

if TYPE_CHECKING:
    import multipoll.models  # noqa: E402


class AbstractScore(electoral_system, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def combine_scores(cls, scores: Iterable[float]) -> float:
        ...

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        if len(votes) == 0:
            return []
        all_scores = [normalize_scores(v.weights[:len(v.options)], 2) for v in votes]
        scores = [cls.combine_scores((s[i] for s in all_scores if s[i] is not None))
                  for i in range(len(votes[0].options))]
        return normalize_scores_with_fixed_max_ints(scores, 100)


class sum_score(AbstractScore):  # noqa: N801
    key = "sumscore"
    label = "Sum of Scores"

    @classmethod
    def combine_scores(cls, scores: Iterable[float]) -> float:
        return sum(scores)


class median_score(AbstractScore):  # noqa: N801
    key = "medianscore"
    label = "Median of Scores"

    @classmethod
    def combine_scores(cls, scores: Iterable[float]) -> float:
        return statistics.median(scores)


class mean_score(AbstractScore):  # noqa: N801
    key = "meanscore"
    label = "Average(Mean) of Scores"

    @classmethod
    def combine_scores(cls, scores: Iterable[float]) -> float:
        return statistics.mean(scores)
