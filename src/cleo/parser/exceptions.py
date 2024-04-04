from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.parser.common import SUPPRESS


if TYPE_CHECKING:
    from cleo.parser.actions import Action


def _get_action_name(argument: Action | None) -> str | None:
    if argument is None:
        return None
    if argument.option_strings:
        return "/".join(argument.option_strings)
    if argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    if argument.dest not in (None, SUPPRESS):
        return argument.dest
    if argument.choices:
        return f"{{{','.join(argument.choices)}}}"
    return None


class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument: Action | None, message: str) -> None:
        self.argument_name: str | None = _get_action_name(argument)
        self.message = message

    def __str__(self) -> str:
        if self.argument_name is None:
            format = f"{self.message}"
        else:
            format = f"argument {self.argument_name}: {self.message}"
        return format


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
