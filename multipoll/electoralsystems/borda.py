from typing import List

from multipoll.electoralsystems.registry import ElectoralSystem, Vote
from multipoll.utils import Numeric


class Borda(ElectoralSystem):
    key = "borda"
    label = "Borda Count"

    @classmethod
    def calculate_weight(cls, ind: int, votes: List[List[Vote]]) -> Numeric:
        return sum((w for _, w in votes[ind] if w is not None))