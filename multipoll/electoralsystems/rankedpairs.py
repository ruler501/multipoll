from __future__ import annotations  # noqa

import logging
from dataclasses import dataclass, field
from typing import Generic, Iterator, List, Optional, Tuple, TypeVar, Union
from typing import TYPE_CHECKING

from django.template.loader import render_to_string

from multipoll.electoralsystems.utils import ElectoralSystem
from multipoll.electoralsystems.utils.ranking import Majority, Ranking

if TYPE_CHECKING:
    import multipoll.models

logger = logging.getLogger(__name__)

_TCov = TypeVar("_TCov", covariant=True)


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
            -> None:
        # x is origin
        # u is intermediate node
        # v is destination
        tree_xu = reachability[x][u]
        tree_jv = reachability[j][v]
        if tree_xu is not None and tree_jv is not None:
            new_tree = Tree[int](v)
            reachability[x][v] = new_tree
            tree_xu.children.append(new_tree)
            for w in tree_jv:
                if reachability[x][w] is None:
                    Tree.meld(reachability, x, j, v, w)
        else:
            logger.warn(f"{x} -> {u} [{tree_xu}] or {j} -> {v} [{tree_jv}] was None")

    @staticmethod
    def calculate_reachability(options_count: int, majorities: List[Majority]) \
            -> Tuple[List[List[Optional[Tree[int]]]],
                     List[Tuple[int, Majority]],
                     List[Tuple[int, Majority]]]:
        reachability: List[List[Optional[Tree[int]]]] = [[None for _2 in range(options_count)]
                                                         for _ in range(options_count)]
        added_edges: List[Tuple[int, Majority]] = []
        skipped_edges: List[Tuple[int, Majority]] = []
        for i in range(options_count):
            reachability[i][i] = Tree[int](i)
        for i, majority in enumerate(majorities):
            if reachability[majority.opposing_option][majority.option] is None:
                added_edges.append((i + 1, majority))
                for x in range(options_count):
                    if reachability[x][majority.option] is not None \
                            and reachability[x][majority.opposing_option] is None:
                        Tree.meld(reachability, x, majority.opposing_option,
                                  majority.option, majority.opposing_option)
            else:
                skipped_edges.append((i + 1, majority))
        return reachability, added_edges, skipped_edges


class ranked_pairs(ElectoralSystem):  # noqa: N801
    key = "ranked_pairs"
    label = "Ranked Pairs"

    @classmethod
    def calculate_reachability_and_edges(cls, votes: List[multipoll.models.FullVoteBase]) \
            -> Tuple[List[List[Optional[Tree]]],
                     List[Tuple[int, Majority]],
                     List[Tuple[int, Majority]]]:
        if len(votes) == 0:
            return ([], [], [])
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
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        if len(votes) == 0:
            return []
        reachability, _, _ = cls.calculate_reachability_and_edges(votes)
        return [sum(1 for t in reachable if t is not None) for reachable in reachability]

    @classmethod
    def visualize_results(cls, question: str, options: List[str],
                          votes: List[multipoll.models.FullVoteBase]) \
            -> Optional[Union[bytes, str]]:
        if len(votes) == 0:
            return None
        reachability, edges, skipped = cls.calculate_reachability_and_edges(votes)
        all_edges = sorted([(i, True, majority) for i, majority in edges]
                           + [(i, False, majority) for i, majority in skipped])
        scores = [sum(1 for t in reachable if t is not None) for reachable in reachability]
        result: List[str] = ['digraph {', f'    label="{question}"', '    pack=false',
                             '    overlap=false', '    splines=polyline', '    newrank=true',
                             '    rankdir="TB"', "    truecolor=true", '    ranksep="1 equally"',
                             '    concentrate=true', '    compress=true']
        result += [f'    n{i} [label="({scores[i]}) \\\\"{option}\\\\""]'
                   for i, option in enumerate(options)]
        graphs: List[str] = ['\n'.join(result + ['}'])]
        for i, used, majority in all_edges:
            source = majority.option
            dest = majority.opposing_option
            margin_str = f"{majority.votes_for} vs. {majority.votes_against} Borda {majority.wins}"
            result[-1] = result[-1].replace('#ff0000', '#000000').replace('#ffaaaa', '#aaaaaa')
            if used:
                result.append(f'    n{source} -> n{dest} [label="({i}) {margin_str}" '
                              + f'color="#ff0000"]')
            else:
                result.append(f'    n{source} -> n{dest} [label="({i}) {margin_str}", '
                              + f'constraint=false, style=dashed, color="#ffaaaa"]')
            graphs.append('\n'.join(result + ['}']))
        return render_to_string('visualize_rankedpairs.html', {'graphs': graphs})
