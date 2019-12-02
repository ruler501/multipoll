from __future__ import annotations  # noqa: T484

from dataclasses import dataclass
from functools import total_ordering
from typing import Iterable, List, Optional, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import multipoll.models


class Ranking:
    weights: List[Optional[float]]
    indexes: List[int]

    def __init__(self, vote: multipoll.models.FullVoteBase, collapse_ties: bool = True):
        options_count = len(vote.poll.options)
        enumerated_weights: List[Tuple[int, int]] = \
            [(i, w) for i, w in enumerate(vote.weights[:options_count]) if w is not None]
        if len(enumerated_weights) == 0:
            self.weights = [None for _ in range(options_count)]
            self.indexes = list(range(options_count))
            return
        prelims = sorted(enumerated_weights, key=lambda x: x[1], reverse=not collapse_ties)
        weights: List[Optional[float]] = [None for _ in range(options_count)]
        cur: Optional[int] = prelims[0][1]
        score: float = 1
        if collapse_ties:
            for i, w in prelims:
                if w != cur:
                    score += 1
                    cur = w
                weights[i] = score
            weights = [None if x is None else (x + len(prelims) - score)  # noqa: IF100
                       for x in weights]
        else:
            for i, w in prelims:
                if w != cur:
                    score = i + 1
                    cur = w
                weights[i] = len(prelims) - score + 1
        self.weights = weights
        none_indexes = [i for i, w in enumerate(vote.weights[:options_count])
                        if w is None]
        self.indexes = [i for i, _ in prelims] + none_indexes


@total_ordering
@dataclass(order=False, frozen=False)
class Majority:
    votes_for: int
    votes_against: int
    wins: int
    option: int
    opposing_option: int

    def __lt__(self, other: object) -> bool:
        return (isinstance(other, self.__class__)
                and (self.votes_for < other.votes_for
                     or (self.votes_for == other.votes_for
                         and (self.votes_against > other.votes_against
                              or (self.votes_against == other.votes_against
                                  and (self.wins < other.wins
                                       or (self.wins == other.wins
                                           and (self.option > other.option
                                                or (self.option == other.option
                                                    and self.opposing_option
                                                    > other.opposing_option)))))))))

    @property
    def margin(self) -> int:
        return self.votes_for - self.votes_against

    @classmethod
    def create(cls, votes_for: int, votes_against: int, wins_for: int, wins_against: int,
               option: int, opposing_option: int) -> Optional[Majority]:
        if votes_for > votes_against:
            return Majority(votes_for, votes_against, wins_for, option, opposing_option)
        elif votes_against > votes_for:
            return Majority(votes_against, votes_for, wins_against, opposing_option, option)
        else:
            return None

    @classmethod
    def populate_majorities(cls, comparisons: List[List[int]]) -> Iterable[Majority]:
        options_count = len(comparisons)
        wins = [0 for _ in range(options_count)]
        for i in range(options_count):
            for j in range(options_count):
                wins[i] += comparisons[i][j]
        for i in range(options_count):
            for j in range(i + 1, options_count):
                majority = Majority.create(comparisons[i][j], comparisons[j][i],
                                           wins[i], wins[j], i, j)
                if majority is not None:
                    yield majority
