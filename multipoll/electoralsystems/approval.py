from typing import List

from multipoll.electoralsystems.registry import ElectoralSystem, Vote


class ApprovalVoting(ElectoralSystem):
    key = "approval"
    label = "Approval"

    @classmethod
    def calculate_weight(cls, ind: int, votes: List[List[Vote]]) -> int:
        return len([1 for _, w in votes[ind] if w is not None and w != 0])