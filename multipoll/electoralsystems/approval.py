from typing import List


# noinspection PyPep8Naming
from multipoll.electoralsystems.registry import electoral_system
from multipoll.models import FullVote


# noinspection PyPep8Naming
class approval(electoral_system):
    key = "approval"
    label = "Approval"

    @classmethod
    def generate_scores(cls, votes: List[FullVote]) -> List[float]:
        if len(votes) == 0:
            return []
        scores = [0 for _ in votes[0].poll.options]
        for vote in votes:
            for i, w in enumerate(vote.weights[:len(scores)]):
                if w:
                    scores[i] += 1
        return scores