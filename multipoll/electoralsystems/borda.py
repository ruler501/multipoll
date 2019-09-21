from typing import List

from multipoll.electoralsystems.ranking import Ranking
from multipoll.electoralsystems.registry import electoral_system
from multipoll.models import FullVote


# noinspection PyPep8Naming
class borda(electoral_system):
    key = "borda"
    label = "Borda Count"

    @classmethod
    def generate_scores(cls, votes: List[FullVote]) -> List[float]:
        rankings = [Ranking(vote) for vote in votes]
        scores = [0 for _ in votes[0].weights]
        for ranking in rankings:
            for i, w in enumerate(ranking.weights):
                if w is not None:
                    scores[i] += w
        return scores