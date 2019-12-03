from __future__ import annotations  # noqa: T484

from typing import List
from typing import TYPE_CHECKING

from multipoll.electoralsystems.utils import ElectoralSystem
from multipoll.utils import FALSEY_VALUES

if TYPE_CHECKING:
    import multipoll.models


class approval(ElectoralSystem):  # noqa: N801
    key = "approval"
    label = "Approval"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        if len(votes) == 0:
            return []
        scores = [0.0 for _ in votes[0].poll.options]
        for vote in votes:
            for i, w in enumerate(vote.weights[:len(scores)]):
                if w and w not in FALSEY_VALUES:
                    scores[i] += 1
        return scores
