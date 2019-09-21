import abc
from typing import List, Tuple, Type

from multipoll.utils import OptNumeric

Vote = Tuple['multipoll.models.User', OptNumeric]
FullVote = 'multipoll.models.FullVote'


class ElectoralSystemMeta(abc.ABCMeta):
    registered_systems = {}

    def __new__(mcs, name, bases, attrs):
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


# noinspection PyPep8Naming
class electoral_system(abc.ABC, metaclass=ElectoralSystemMeta):
    @classmethod
    def order_options(cls, options: List[str], votes: List[FullVote]) -> List[Tuple[str, List[Vote], float]]:
        scores = cls.generate_scores(votes)
        return [p for p
                in sorted(zip(options, votes, scores),
                          key=lambda o: o[2], reverse=True)]

    @classmethod
    @abc.abstractmethod
    def generate_scores(cls, votes: List[FullVote]) -> List[float]: ...


def get_electoral_system(key: str) -> Type[electoral_system]:
    return ElectoralSystemMeta.registered_systems[key]