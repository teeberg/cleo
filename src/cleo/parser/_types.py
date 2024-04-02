from __future__ import annotations

from typing import TYPE_CHECKING
from typing import NewType
from typing import Protocol


if TYPE_CHECKING:
    from cleo.parser.parser import HelpFormatter


class _FormatterClass(Protocol):
    def __call__(self, *, prog: str) -> HelpFormatter: ...


_SUPPRESS_T = NewType("_SUPPRESS_T", str)
