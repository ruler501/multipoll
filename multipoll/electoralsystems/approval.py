from __future__ import annotations  # noqa: T484

from typing import List, TypeVar

import multipoll.models
from multipoll.electoralsystems.registry import electoral_system

Numeric = TypeVar('Numeric')


# noinspection PyPep8Naming
class approval(electoral_system):  # noqa: N801
    key = "approval"
    label = "Approval"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase[Numeric]]) -> List[float]:
        if len(votes) == 0:
            return []
        scores: List[float] = [0.0 for _ in votes[0].poll.options]
        for vote in votes:
            for i, w in enumerate(vote.weights[:len(scores)]):
                if w:
                    scores[i] += 1
        return scores