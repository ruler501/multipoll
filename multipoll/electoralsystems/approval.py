from typing import List, Tuple

from multipoll.electoralsystems.registry import ElectoralSystem, Vote
from multipoll.utils import Numeric


class ApprovalVoting(ElectoralSystem):
    key = "approval"
    label = "Approval"

    @classmethod
    def calculate_weight(cls, ind: int, votes: List[List[Vote]]) -> Numeric:
        return  len([1 for _, w in votes[ind] if w != 0])