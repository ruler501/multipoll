from __future__ import annotations  # noqa

from typing import List, TypeVar

import multipoll.models
from multipoll.electoralsystems.ranking import Ranking
from multipoll.electoralsystems.registry import electoral_system

Numeric = TypeVar('Numeric')


# noinspection PyPep8Naming
class borda(electoral_system):
    key = "borda"
    label = "Borda Count"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase[Numeric]]) -> List[float]:
        rankings = [Ranking(vote) for vote in votes]
        scores: List[float] = [0.0 for _ in votes[0].weights]
        for ranking in rankings:
            for i, w in enumerate(ranking.weights):
                if w is not None:
                    scores[i] += w
        return scores