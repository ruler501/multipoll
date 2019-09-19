import abc
from typing import List, Tuple

from multipoll.utils import Numeric, OptNumeric

Vote = Tuple['multipoll.models.User', OptNumeric]


class ElectoralSystemMeta(abc.ABCMeta):
    registered_systems = {}

    def __new__(mcs, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, ElectoralSystemMeta)]
        new_type = super().__new__(mcs, name, bases, attrs)
        if parents:
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


class ElectoralSystem(metaclass=ElectoralSystemMeta):
    @classmethod
    def order_options(cls, options: List[str], votes: List[List[Vote]]) -> List[Tuple[str, List[Vote]]]:
        # noinspection PyTypeChecker
        return [p for _, p
                in sorted(enumerate(zip(options, votes)),
                          key=lambda o: cls.calculate_weight(o[0], votes), reverse=True)]

    @classmethod
    @abc.abstractmethod
    def calculate_weight(cls, ind: int, votes: List[List[Vote]]) -> Numeric: ...


def get_electoral_system(key: str):
    return ElectoralSystemMeta.registered_systems[key]