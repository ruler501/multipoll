from __future__ import annotations  # noqa: T484

import abc
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import multipoll.models


class ElectoralSystemMeta(abc.ABCMeta):
    registered_systems: Dict[str, Type[electoral_system]] = {}

    def __new__(mcs, name: str, bases: Tuple[Type, ...],  # noqa: N804
                attrs: Dict[str, Any]) -> Type[electoral_system]:
        parents = [b for b in bases if b is abc.ABC]
        new_type = super().__new__(mcs, name, bases, attrs)
        if not parents:
            key = getattr(new_type, 'key', None)
            if key is None:
                key = name
                setattr(new_type, "key", key)
            label = getattr(new_type, "label", None)
            if label is None:
                label = name
                setattr(new_type, "label", label)
            ElectoralSystemMeta.registered_systems[key] = new_type
        return new_type


class electoral_system(abc.ABC, metaclass=ElectoralSystemMeta):  # noqa: N801
    @classmethod
    def order_options(cls, options: List[str],
                      votes: List[multipoll.models.FullVoteBase]) \
            -> List[Tuple[str, List[Tuple[multipoll.models.User, Optional[Any]]], float]]:
        scores = cls.generate_scores(votes)
        collected_votes: List[List[Tuple[multipoll.models.User, Optional[Any]]]] = \
            [[] for _ in options]
        for vote in votes:
            for i, w in enumerate(vote.weights):
                if w is not None:
                    collected_votes[i].append((vote.user, w))
        return sorted(zip(options, collected_votes, scores), key=lambda o: o[2], reverse=True)

    @classmethod
    @abc.abstractmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        ...

    @classmethod
    def visualize_results(cls, options: List[str],
                          votes: List[multipoll.models.FullVoteBase]) \
            -> Optional[Union[bytes, str]]:
        return None


def get_electoral_system(key: str) -> Type[electoral_system]:
    return ElectoralSystemMeta.registered_systems[key]
