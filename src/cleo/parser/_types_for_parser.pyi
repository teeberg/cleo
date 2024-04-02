# import sys
#
# from collections.abc import Callable
# from collections.abc import Generator
# from collections.abc import Iterable
# from collections.abc import Sequence
# from re import Pattern
# from typing import IO
# from typing import Any
# from typing import Generic
# from typing import Literal
# from typing import NewType
# from typing import NoReturn
# from typing import Protocol
# from typing import TypeVar
# from typing import overload
#
# from _typeshed import sentinel
# from typing_extensions import Self
# from typing_extensions import TypeAlias
# from typing_extensions import deprecated
#
# __all__ = [
#     "ArgumentParser",
#     "ArgumentError",
#     "ArgumentTypeError",
#     "FileType",
#     "HelpFormatter",
#     "ArgumentDefaultsHelpFormatter",
#     "RawDescriptionHelpFormatter",
#     "RawTextHelpFormatter",
#     "MetavarTypeHelpFormatter",
#     "Namespace",
#     "Action",
#     "ONE_OR_MORE",
#     "OPTIONAL",
#     "PARSER",
#     "REMAINDER",
#     "SUPPRESS",
#     "ZERO_OR_MORE",
# ]
#
# if sys.version_info >= (3, 9):
#     __all__ += ["BooleanOptionalAction"]
#
# _T = TypeVar("_T")
# _ActionT = TypeVar("_ActionT", bound=Action)
# _ArgumentParserT = TypeVar("_ArgumentParserT", bound=ArgumentParser)
# _N = TypeVar("_N")
# # more precisely, Literal["store", "store_const", "store_true",
# # "store_false", "append", "append_const", "count", "help", "version",
# # "extend"], but using this would make it hard to annotate callers
# # that don't use a literal argument
# _ActionStr: TypeAlias = str
# # more precisely, Literal["?", "*", "+", "...", "A...",
# # "==SUPPRESS=="], but using this would make it hard to annotate
# # callers that don't use a literal argument
# _NArgsStr: TypeAlias = str
#
# ONE_OR_MORE: Literal["+"]
# OPTIONAL: Literal["?"]
# PARSER: Literal["A..."]
# REMAINDER: Literal["..."]
# _SUPPRESS_T = NewType("_SUPPRESS_T", str)
# SUPPRESS: (
#     _SUPPRESS_T | str
# )  # not using Literal because argparse sometimes compares SUPPRESS with is
# # the | str is there so that foo = argparse.SUPPRESS; foo = "test" checks out in mypy
# ZERO_OR_MORE: Literal["*"]
# _UNRECOGNIZED_ARGS_ATTR: str  # undocumented
#
# class _ActionsContainer:
#     def add_argument(
#         self,
#         *name_or_flags: str,
#         action: _ActionStr | type[Action] = ...,
#         nargs: int | _NArgsStr | _SUPPRESS_T | None = None,
#         const: Any = ...,
#         default: Any = ...,
#         type: Callable[[str], _T] | FileType = ...,
#         choices: Iterable[_T] | None = ...,
#         required: bool = ...,
#         help: str | None = ...,
#         metavar: str | tuple[str, ...] | None = ...,
#         dest: str | None = ...,
#         version: str = ...,
#         **kwargs: Any,
#     ) -> Action: ...
#     def add_argument_group(
#         self,
#         title: str | None = None,
#         description: str | None = None,
#         *,
#         prefix_chars: str = ...,
#         argument_default: Any = ...,
#         conflict_handler: str = ...,
#     ) -> _ArgumentGroup: ...
#     def add_mutually_exclusive_group(
#         self, *, required: bool = False
#     ) -> _MutuallyExclusiveGroup: ...
#
# class ArgumentParser(_AttributeHolder, _ActionsContainer):
#     prog: str
#     usage: str | None
#     epilog: str | None
#     formatter_class: _FormatterClass
#     fromfile_prefix_chars: str | None
#     add_help: bool
#     allow_abbrev: bool
#
#     # undocumented
#     _positionals: _ArgumentGroup
#     _optionals: _ArgumentGroup
#     _subparsers: _ArgumentGroup | None
#
#     # Note: the constructor arguments are also used in _SubParsersAction.add_parser.
#     if sys.version_info >= (3, 9):
#         def __init__(
#             self,
#             prog: str | None = None,
#             usage: str | None = None,
#             description: str | None = None,
#             epilog: str | None = None,
#             parents: Sequence[ArgumentParser] = [],
#             formatter_class: _FormatterClass = ...,
#             prefix_chars: str = "-",
#             fromfile_prefix_chars: str | None = None,
#             argument_default: Any = None,
#             conflict_handler: str = "error",
#             add_help: bool = True,
#             allow_abbrev: bool = True,
#             exit_on_error: bool = True,
#         ) -> None: ...
#     else:
#         def __init__(
#             self,
#             prog: str | None = None,
#             usage: str | None = None,
#             description: str | None = None,
#             epilog: str | None = None,
#             parents: Sequence[ArgumentParser] = [],
#             formatter_class: _FormatterClass = ...,
#             prefix_chars: str = "-",
#             fromfile_prefix_chars: str | None = None,
#             argument_default: Any = None,
#             conflict_handler: str = "error",
#             add_help: bool = True,
#             allow_abbrev: bool = True,
#         ) -> None: ...
#
#     @overload
#     def parse_args(
#         self, args: Sequence[str] | None = None, namespace: None = None
#     ) -> Namespace: ...
#     @overload
#     def parse_args(self, args: Sequence[str] | None, namespace: _N) -> _N: ...
#     @overload
#     def parse_args(self, *, namespace: _N) -> _N: ...
#     @overload
#     def add_subparsers(
#         self: _ArgumentParserT,
#         *,
#         title: str = ...,
#         description: str | None = ...,
#         prog: str = ...,
#         action: type[Action] = ...,
#         option_string: str = ...,
#         dest: str | None = ...,
#         required: bool = ...,
#         help: str | None = ...,
#         metavar: str | None = ...,
#     ) -> _SubParsersAction[_ArgumentParserT]: ...
#     @overload
#     def add_subparsers(
#         self,
#         *,
#         title: str = ...,
#         description: str | None = ...,
#         prog: str = ...,
#         parser_class: type[_ArgumentParserT],
#         action: type[Action] = ...,
#         option_string: str = ...,
#         dest: str | None = ...,
#         required: bool = ...,
#         help: str | None = ...,
#         metavar: str | None = ...,
#     ) -> _SubParsersAction[_ArgumentParserT]: ...
#     def print_usage(self, file: IO[str] | None = None) -> None: ...
#     def print_help(self, file: IO[str] | None = None) -> None: ...
#     def format_usage(self) -> str: ...
#     def format_help(self) -> str: ...
#     @overload
#     def parse_known_args(
#         self, args: Sequence[str] | None = None, namespace: None = None
#     ) -> tuple[Namespace, list[str]]: ...
#     @overload
#     def parse_known_args(
#         self, args: Sequence[str] | None, namespace: _N
#     ) -> tuple[_N, list[str]]: ...
#     @overload
#     def parse_known_args(self, *, namespace: _N) -> tuple[_N, list[str]]: ...
#     def convert_arg_line_to_args(self, arg_line: str) -> list[str]: ...
#     def exit(self, status: int = 0, message: str | None = None) -> NoReturn: ...
#     def error(self, message: str) -> NoReturn: ...
#     @overload
#     def parse_intermixed_args(
#         self, args: Sequence[str] | None = None, namespace: None = None
#     ) -> Namespace: ...
#     @overload
#     def parse_intermixed_args(
#         self, args: Sequence[str] | None, namespace: _N
#     ) -> _N: ...
#     @overload
#     def parse_intermixed_args(self, *, namespace: _N) -> _N: ...
#     @overload
#     def parse_known_intermixed_args(
#         self, args: Sequence[str] | None = None, namespace: None = None
#     ) -> tuple[Namespace, list[str]]: ...
#     @overload
#     def parse_known_intermixed_args(
#         self, args: Sequence[str] | None, namespace: _N
#     ) -> tuple[_N, list[str]]: ...
#     @overload
#     def parse_known_intermixed_args(self, *, namespace: _N) -> tuple[_N, list[str]]: ...
#     # undocumented
#     def _get_optional_actions(self) -> list[Action]: ...
#     def _get_positional_actions(self) -> list[Action]: ...
#     def _parse_known_args(
#         self, arg_strings: list[str], namespace: Namespace
#     ) -> tuple[Namespace, list[str]]: ...
#     def _read_args_from_files(self, arg_strings: list[str]) -> list[str]: ...
#     def _match_argument(self, action: Action, arg_strings_pattern: str) -> int: ...
#     def _match_arguments_partial(
#         self, actions: Sequence[Action], arg_strings_pattern: str
#     ) -> list[int]: ...
#     def _parse_optional(
#         self, arg_string: str
#     ) -> tuple[Action | None, str, str | None] | None: ...
#     def _get_option_tuples(
#         self, option_string: str
#     ) -> list[tuple[Action, str, str | None]]: ...
#     def _get_nargs_pattern(self, action: Action) -> str: ...
#     def _get_values(self, action: Action, arg_strings: list[str]) -> Any: ...
#     def _get_value(self, action: Action, arg_string: str) -> Any: ...
#     def _check_value(self, action: Action, value: Any) -> None: ...
#     def _get_formatter(self) -> HelpFormatter: ...
#     def _print_message(self, message: str, file: IO[str] | None = None) -> None: ...
#
# # undocumented
# class _SubParsersAction(Action, Generic[_ArgumentParserT]):
#     _ChoicesPseudoAction: type[Any]  # nested class
#
#     # Note: `add_parser` accepts all kwargs of `ArgumentParser.__init__`. It also
#     # accepts its own `help` and `aliases` kwargs.
#     if sys.version_info >= (3, 9):
#         def add_parser(
#             self,
#             name: str,
#             *,
#             help: str | None = ...,
#             aliases: Sequence[str] = ...,
#             # Kwargs from ArgumentParser constructor
#             prog: str | None = ...,
#             usage: str | None = ...,
#             description: str | None = ...,
#             epilog: str | None = ...,
#             parents: Sequence[_ArgumentParserT] = ...,
#             formatter_class: _FormatterClass = ...,
#             prefix_chars: str = ...,
#             fromfile_prefix_chars: str | None = ...,
#             argument_default: Any = ...,
#             conflict_handler: str = ...,
#             add_help: bool = ...,
#             allow_abbrev: bool = ...,
#             exit_on_error: bool = ...,
#         ) -> _ArgumentParserT: ...
#     else:
#         def add_parser(
#             self,
#             name: str,
#             *,
#             help: str | None = ...,
#             aliases: Sequence[str] = ...,
#             # Kwargs from ArgumentParser constructor
#             prog: str | None = ...,
#             usage: str | None = ...,
#             description: str | None = ...,
#             epilog: str | None = ...,
#             parents: Sequence[_ArgumentParserT] = ...,
#             formatter_class: _FormatterClass = ...,
#             prefix_chars: str = ...,
#             fromfile_prefix_chars: str | None = ...,
#             argument_default: Any = ...,
#             conflict_handler: str = ...,
#             add_help: bool = ...,
#             allow_abbrev: bool = ...,
#         ) -> _ArgumentParserT: ...
