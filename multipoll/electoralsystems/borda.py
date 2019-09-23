from __future__ import annotations  # noqa

from typing import List, TypeVar

import multipoll.models
from multipoll.electoralsystems.ranking import Ranking
from multipoll.electoralsystems.registry import electoral_system

Numeric = TypeVar('Numeric')


# noinspection PyPep8Naming
class borda(electoral_system):  # noqa: N801
    key = "borda"
    label = "Borda Count"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase[Numeric]]) -> List[float]:
        if len(votes) == 0:
            return []
        rankings = [Ranking(vote) for vote in votes]
        option_count = len(votes[0].poll.options)
        scores: List[float] = [0.0 for _ in range(option_count)]
        for ranking in rankings:
            for i, w in enumerate(ranking.weights[:option_count]):
                if w is not None:
                    scores[i] += w
        return scores