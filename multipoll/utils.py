import logging
import os

from typing import TypeVar, List, Callable, Iterable, Set, Optional

T = TypeVar('T')
U = TypeVar('U')
Numeric = TypeVar('Numeric', bool, int, float)
OptNumeric = Optional[Numeric]

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
def unique_iter(seq: Iterable[T], id_function: Callable[[T], U] = lambda x: x) -> Iterable[T]:
    """Originally proposed by Andrew Dalke."""
    seen: Set[T] = set()
    for x in seq:
        y = id_function(x)
        if y not in seen:
            seen.add(y)
            yield x


# TODO: Figure out how to make the type signature work with the default argument
def unique_list(seq: Iterable[T], id_function: Callable[[T], U] = lambda x: x) -> List[T]:  # Order preserving
    return list(unique_iter(seq, id_function))


class ClassProperty(object):
    # noinspection SpellCheckingInspection
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)