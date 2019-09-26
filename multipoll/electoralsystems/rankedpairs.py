from __future__ import annotations  # noqa

import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Generic, Iterable, Iterator, List, Optional, Tuple, TypeVar, Union

from multipoll.electoralsystems.ranking import Ranking
from multipoll.electoralsystems.registry import electoral_system
from multipoll.models import FullVoteBase

Numeric = TypeVar('Numeric')
_TCov = TypeVar("_TCov", covariant=True)


@total_ordering
@dataclass(order=False, frozen=False)
class Majority:
    votes_for: int
    votes_against: int
    option: int
    opposing_option: int

    def __lt__(self, other: object) -> bool:
        return (isinstance(other, self.__class__)
                and (self.votes_for < other.votes_for
                     or (self.votes_for == other.votes_for
                         and (self.votes_against > other.votes_against
                              or (self.votes_against == other.votes_against
                                  and (self.option > other.option
                                       or (self.option == other.option
                                           and self.opposing_option > other.opposing_option)))))))

    @property
    def margin(self) -> int:
        return self.votes_for - self.votes_against

    @classmethod
    def create(cls, votes_for: int, votes_against: int, option: int,
               opposing_option: int) -> Optional[Majority]:
        if votes_for > votes_against:
            return Majority(votes_for, votes_against, option, opposing_option)
        elif votes_against > votes_for:
            return Majority(votes_against, votes_for, opposing_option, option)
        else:
            return None

    @classmethod
    def populate_majorities(cls, comparisons: List[List[int]]) -> Iterable[Majority]:
        options_count = len(comparisons)
        for i in range(options_count):
            for j in range(i + 1, options_count):
                majority = Majority.create(comparisons[i][j], comparisons[j][i], i, j)
                if majority is not None:
                    yield majority


@dataclass
class Tree(Generic[_TCov]):
    value: _TCov
    children: List[Tree[_TCov]] = field(default_factory=list, init=False)

    def __iter__(self) -> Iterator[_TCov]:
        yield self.value
        for child in self.children:
            yield from iter(child)

    @staticmethod
    def meld(reachability: List[List[Optional[Tree[int]]]], x: int, j: int, u: int, v: int) \
            -> List[Tuple[int, int]]:
        tree_xu = reachability[x][u]
        tree_jv = reachability[j][v]
        result: List[Tuple[int, int]] = []
        if tree_xu is not None and tree_jv is not None:
            new_tree = Tree[int](v)
            reachability[x][v] = new_tree
            result.append((x, v))
            tree_xu.children.append(new_tree)
            for w in tree_jv:
                if reachability[x][w] is None:
                    result += Tree[int].meld(reachability, x, j, v, w)
        return result

    @staticmethod
    def calculate_reachability(options_count: int, majorities: List[Majority]) \
            -> Tuple[List[List[Optional[Tree[int]]]], List[Tuple[int, int]]]:
        reachability: List[List[Optional[Tree[int]]]] = [[None for _2 in range(options_count)]
                                                         for _ in range(options_count)]
        added_edges: List[Tuple[int, int]] = []
        for i in range(options_count):
            reachability[i][i] = Tree[int](i)
        for majority in majorities:
            if reachability[majority.option][majority.opposing_option] is None:
                for x in range(options_count):
                    if reachability[x][majority.option] is not None \
                            and reachability[x][majority.opposing_option] is None:
                        added_edges += Tree.meld(reachability, x, majority.opposing_option,
                                                 majority.option, majority.opposing_option)
        return reachability, added_edges


# noinspection PyPep8Naming
class ranked_pairs(electoral_system):  # noqa: N801
    key = "rankedpairs"
    label = "Ranked Pairs"

    @classmethod
    def calculate_reachability_and_edges(cls, votes: List[FullVoteBase[Numeric]]) \
            -> Tuple[List[List[Optional[Tree[int]]]], List[Tuple[int, int]]]:
        if len(votes) == 0:
            return ([], [])
        rankings = [Ranking(vote) for vote in votes]
        options_count = len(rankings[0].indexes)
        comparisons: List[List[int]] = [[0 for _2 in range(options_count)]
                                        for _ in range(options_count)]
        for ranking in rankings:
            for i, w in enumerate(ranking.weights):
                if w is not None:
                    for j0, w2 in enumerate(ranking.weights[i + 1:]):
                        if w2 is None:
                            continue
                        elif w > w2:
                            comparisons[i][j0 + i + 1] += 1
                        elif w2 > w:
                            comparisons[j0 + i + 1][i] += 1
        majorities = sorted(Majority.populate_majorities(comparisons), reverse=True)
        return Tree[int].calculate_reachability(options_count, majorities)

    @classmethod
    def generate_scores(cls, votes: List[FullVoteBase[Numeric]]) -> List[float]:
        if len(votes) == 0:
            return []
        reachability, _ = cls.calculate_reachability_and_edges(votes)
        return [sum(1 for t in reachable if t is not None) for reachable in reachability]

    @classmethod
    def visualize_results(cls, question: str, options: List[str],
                          votes: List[FullVoteBase[Numeric]]) \
            -> Optional[Union[bytes, str]]:
        if len(votes) == 0:
            return None
        reachability, edges = cls.calculate_reachability_and_edges(votes)
        scores = [sum(1 for t in reachable if t is not None) for reachable in reachability]
        result: List[str] = [f'digraph [label="{question}"] ' + '{']
        result += [f'    n{i} [label="{option}({scores[i]})"]' for i, option in enumerate(options)]
        result += [f'    n{p[0]} -> n{p[1]} [label="{i}"]' for i, p in enumerate(edges)]
        result += ['}']
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfilepath = f'{tmpdir}/result.dot'
            with open(tmpfilepath, 'w') as tmpsourcefile:
                tmpsourcefile.write('\n'.join(result))
            resultfilepath = f'{tmpdir}/result.svg'
            subprocess.run(['dot', '-Tsvg', '-o', resultfilepath, tmpfilepath])
            with open(resultfilepath, 'r') as tmpresultfile:
                return tmpresultfile.read()
