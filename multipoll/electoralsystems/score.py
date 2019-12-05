from __future__ import annotations  # noqa

import abc
import statistics
from typing import List, Union
from typing import TYPE_CHECKING

from django.utils.decorators import classproperty

from multipoll.electoralsystems.utils import ElectoralSystem
from multipoll.electoralsystems.utils.cardinalscores import INFINITY
from multipoll.electoralsystems.utils.cardinalscores import InfinityType
from multipoll.electoralsystems.utils.cardinalscores import normalize_scores, \
    normalize_scores_with_fixed_max_ints

if TYPE_CHECKING:
    import multipoll.models  # noqa: E402


class AbstractScore(ElectoralSystem, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def combine_scores(cls, scores: List[float]) -> float:
        ...

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return 2

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        if len(votes) == 0:
            return []
        all_scores = [normalize_scores(v.weights[:len(v.options)], cls.dim) for v in votes]
        scores = [cls.combine_scores([s[i] for s in all_scores if s[i] is not None])
                  for i in range(len(votes[0].options))]
        return [None if s is None else int(100*s) for s in scores]  # noqa: IF100
        return normalize_scores_with_fixed_max_ints(scores, 100)


class sum_score(AbstractScore):  # noqa: N801
    key = "sum_score"
    label = "Sum of Scores with L-2(Euclidean) Norm"

    @classmethod
    def combine_scores(cls, scores: List[float]) -> float:
        if len(scores) == 0:
            return 0
        return sum(scores)


class median_score(AbstractScore):  # noqa: N801
    key = "median_score"
    label = "Median of Scores with L-2(Euclidean) Norm"

    @classmethod
    def combine_scores(cls, scores: List[float]) -> float:
        if len(scores) == 0:
            return 0
        return statistics.median(scores)


class mean_score(AbstractScore):  # noqa: N801
    key = "mean_score"
    label = "Average(Mean) of Scores with L-2(Euclidean) Norm"

    @classmethod
    def combine_scores(cls, scores: List[float]) -> float:
        if len(scores) == 0:
            return 0
        return statistics.mean(scores)


class sum_score_infinity(sum_score):  # noqa: N801
    key = "sum_score_infinity"
    label = "Sum of Scores with L-Infinity(max) Norm"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return INFINITY


class median_score_infinity(median_score):  # noqa: N801
    key = "median_score_infinity"
    label = "Median of Scores with L-Infinity(max) Norm"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return INFINITY


class mean_score_infinity(mean_score):  # noqa: N801
    key = "mean_score_infinity"
    label = "Average(Mean) of Scores with L-Infinity(max norm)"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return INFINITY


class sum_score_manhattan(sum_score):  # noqa: N801
    key = "sum_score_manhattan"
    label = "Sum of Scores with L-1(Manhattan) Norm"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return 1


class median_score_manhattan(median_score):  # noqa: N801
    key = "median_score_manhattan"
    label = "Median of Scores with L-1(Manhattan) Norm"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return 1


class mean_score_manhattan(mean_score):  # noqa: N801
    key = "mean_score_manhattan"
    label = "Average(Mean) of Scores with L-1(Manhattan) Norm"

    @classproperty
    def dim(cls) -> Union[int, InfinityType]:  # noqa: N805
        return 1
