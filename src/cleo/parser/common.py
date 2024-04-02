from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from cleo.parser._types import _SUPPRESS_T


SUPPRESS: _SUPPRESS_T | str = "==SUPPRESS=="
_UNRECOGNIZED_ARGS_ATTR = "_unrecognized_args"


class NArgsEnum(str, Enum):
    OPTIONAL = "?"
    ZERO_OR_MORE = "*"
    ONE_OR_MORE = "+"
    PARSER = "A..."
    REMAINDER = "..."


T = TypeVar("T")


def _copy_items(items: T) -> T:
    if items is None:
        return []
    # The copy module is used only in the 'append' and 'append_const'
    # actions, and it is needed only when the default value isn't a list.
    # Delay its import for speeding up the common case.
    if isinstance(items, list):
        return items[:]
    import copy

    return copy.copy(items)
