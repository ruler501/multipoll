from __future__ import annotations  # noqa

from typing import List
from typing import TYPE_CHECKING

from multipoll.electoralsystems.utils import ElectoralSystem
from multipoll.electoralsystems.utils.ranking import Ranking

if TYPE_CHECKING:
    import multipoll.models  # noqa: E402


class borda(ElectoralSystem):  # noqa: N801
    key = "borda"
    label = "Borda Count"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
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
