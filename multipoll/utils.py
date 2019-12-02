import logging
import os
from typing import Any, Callable, Generic, Iterable, List, Optional, Set, Type, TypeVar

T = TypeVar('T')
TContra = TypeVar('TContra', contravariant=True)
UCov = TypeVar('UCov', covariant=True)

logger = logging.getLogger(__name__)

client_id = "4676884434.375651972439"
client_secret = os.environ.get("MPOLLS_CLIENT_SECRET", "")
bot_secret = os.environ.get("MPOLLS_BOT_SECRET", "")


def absolute_url_without_request(location: str) -> str:
    current_site = os.environ.get("MPOLLS_HOST", "localhost:8000")
    return f"https://{current_site}{location}"


def collapse_lists(lists: List[List[str]]) -> List[List[str]]:
    if len(lists) == 0:
        return lists
    result = [['' for _ in lists[0]]]
    for l in lists:
        for i, item in enumerate(l):
            for res in result:
                if res[i] == '' and res[0] == l[0]:
                    res[i] = item
                    break
            else:
                result.append(['' for _ in lists[0]])
                result[-1][0] = l[0]
                result[-1][i] = item
    return result


# TODO: Figure out how to make the type signature work with the default argument
def unique_iter(seq: Iterable[T], key_function: Optional[Callable[[T], Any]] = None) \
        -> Iterable[T]:
    """Originally proposed by Andrew Dalke."""
    seen: Set = set()
    for x in seq:
        if key_function:
            y = key_function(x)
        else:
            y = x
        if y not in seen:
            seen.add(y)
            yield x


# Order preserving
# TODO: Figure out how to make the type signature work with the default argument
def unique_list(seq: Iterable[T], key_function: Optional[Callable[[T], Any]] = None) \
        -> List[T]:
    return list(unique_iter(seq, key_function))


class ClassProperty(Generic[TContra, UCov]):
    def __init__(self, fget: Callable[[Type[TContra]], UCov]):
        self.fget = fget

    def __get__(self, owner_self: Optional[TContra], owner_cls: Type[TContra]) -> UCov:
        return self.fget(owner_cls)
