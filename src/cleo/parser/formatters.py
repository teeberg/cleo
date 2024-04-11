from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from typing import Sequence

from cleo._utils import get_indented_string
from cleo.parser.common import SUPPRESS
from cleo.parser.common import NArgsEnum
from cleo.terminal import Terminal


if TYPE_CHECKING:
    from typing_extensions import Self

    from cleo.parser.actions import Action
    from cleo.parser.parser import _MutuallyExclusiveGroup


# ===============
# Formatting Help
# ===============


class HelpFormatter:
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ) -> None:
        self._prog = prog
        self._indent_increment = indent_increment
        self._width: int = width or Terminal().width - 2
        self._max_help_position = min(
            max_help_position, max(self._width - 20, indent_increment * 2)
        )

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = re.compile(r"\s+", re.ASCII)
        self._long_break_matcher = re.compile(r"\n\n\n+")

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self) -> None:
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self) -> None:
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, "Indent decreased below 0."
        self._level -= 1

    class _Section:
        def __init__(
            self,
            formatter: HelpFormatter,
            parent: Self | None,
            heading: str | None = None,
        ):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items: list[tuple[Callable[..., str], Iterable[Any]]] = []

        def format_help(self) -> str:
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ""

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = f"{get_indented_string(self.heading, current_indent)}:\n"
            else:
                heading = ""

            # join the section-initial newline, the heading and the help
            return join(["\n", heading, item_help, "\n"])

    def _add_item(self, func: Callable[..., str], args: Iterable[Any]) -> None:
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading: str | None) -> None:
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self) -> None:
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text: str | None) -> None:
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(
        self,
        usage: str | None,
        actions: Iterable[Action],
        groups: Iterable[_MutuallyExclusiveGroup],
        prefix: str | None = None,
    ) -> None:
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action: Action) -> None:
        if action.help is not SUPPRESS:
            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            invocations.extend(
                [
                    get_invocation(subaction)
                    for subaction in self._iter_indented_subactions(action)
                ]
            )

            # update the maximum item length
            invocation_length = max(map(len, invocations))
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions: Iterable[Action]) -> None:
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self) -> str:
        if formatted_help := self._root_section.format_help():
            formatted_help = self._long_break_matcher.sub("\n\n", formatted_help).strip(
                "\n"
            )
            formatted_help += "\n"
        return formatted_help

    @staticmethod
    def _join_parts(part_strings: Iterable[str]) -> str:
        return "".join([part for part in part_strings if part and part is not SUPPRESS])

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[Action],
        groups: Iterable[_MutuallyExclusiveGroup],
        prefix: str | None = None,
    ) -> str:
        prefix = "usage: " if prefix is None else prefix

        # if usage is specified, use that
        if usage is not None:
            usage = usage.format(prog=self._prog)
        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = f"{self._prog}"

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = f"{self._prog}"

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            action_usage = self._format_actions_usage(optionals + positionals, groups)
            usage = " ".join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:
                # break usage into wrappable parts
                part_regexp = r"\(.*?\)+(?=\s|$)|" r"\[.*?\]+(?=\s|$)|" r"\S+"
                opt_usage = self._format_actions_usage(optionals, groups)
                pos_usage = self._format_actions_usage(positionals, groups)
                opt_parts = re.findall(part_regexp, opt_usage)
                pos_parts = re.findall(part_regexp, pos_usage)
                assert " ".join(opt_parts) == opt_usage
                assert " ".join(pos_parts) == pos_usage

                # helper for wrapping lines
                def get_lines(
                    parts: list[str], indent: str, prefix: str | None = None
                ) -> list[str]:
                    lines: list[str] = []
                    line: list[str] = []
                    indent_length = len(indent)
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = indent_length - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width and line:
                            lines.append(indent + " ".join(line))
                            line = []
                            line_len = indent_length - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + " ".join(line))
                    if prefix is not None:
                        lines[0] = lines[0][indent_length:]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = " " * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog, *opt_parts], indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog, *pos_parts], indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = " " * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog, *lines]

                # join lines into usage
                usage = "\n".join(lines)

        # prefix with 'usage:'
        return f"{prefix}{usage}\n\n"

    def _format_actions_usage(
        self, actions: Sequence[Action], groups: Iterable[_MutuallyExclusiveGroup]
    ) -> str:
        # find group indices and identify actions in groups
        group_actions = set()
        inserts: dict[int, str] = {}
        for group in groups:
            if not group._group_actions:
                raise ValueError(f"empty group {group}")

            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                group_action_count = len(group._group_actions)
                end = start + group_action_count
                if actions[start:end] == group._group_actions:
                    suppressed_actions_count = 0
                    for action in group._group_actions:
                        group_actions.add(action)
                        if action.help is SUPPRESS:
                            suppressed_actions_count += 1

                    exposed_actions_count = (
                        group_action_count - suppressed_actions_count
                    )

                    if not group.required:
                        if start in inserts:
                            inserts[start] += " ["
                        else:
                            inserts[start] = "["
                        if end in inserts:
                            inserts[end] += "]"
                        else:
                            inserts[end] = "]"
                    elif exposed_actions_count > 1:
                        if start in inserts:
                            inserts[start] += " ("
                        else:
                            inserts[start] = "("
                        if end in inserts:
                            inserts[end] += ")"
                        else:
                            inserts[end] = ")"
                    for i in range(start + 1, end):
                        inserts[i] = "|"

        # collect all actions format strings
        parts: list[str | None] = []
        for i, action in enumerate(actions):
            # suppressed arguments are marked with None
            # remove | separators for suppressed arguments
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == "|":
                    inserts.pop(i)
                elif inserts.get(i + 1) == "|":
                    inserts.pop(i + 1)

            # produce all arg strings
            elif not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                part = self._format_args(action, default)

                # if it's in a group, strip the outer []
                if action in group_actions and part[0] == "[" and part[-1] == "]":
                    part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = action.format_usage()

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    part = f"{option_string} {args_string}"

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = f"[{part}]"

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = " ".join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r"[\[(]"
        close = r"[\])]"
        text = re.sub(rf"({open}) ", r"\1", text)
        text = re.sub(rf" ({close})", r"\1", text)
        text = re.sub(rf"{open} *{close}", r"", text)

        # return the text
        return text.strip()

    def _format_text(self, text: str) -> str:
        if "{prog}" in text:
            text = text.format(prog=self._prog)
        text_width = max(self._width - self._current_indent, 11)
        return self._fill_text(text, text_width, self._current_indent) + "\n\n"

    def _format_action(self, action: Action) -> str:
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # no help; start on same line and add a final newline
        if not action.help:
            action_header = (
                f"{get_indented_string(action_header, self._current_indent)}\n"
            )

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            action_header = f"{action_header:<{action_width}}"
            action_header = (
                f"{get_indented_string(action_header, self._current_indent)}  "
            )
            indent_first = 0

        # long action name; start on the next line
        else:
            action_header = (
                f"{get_indented_string(action_header, self._current_indent)}\n"
            )
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help and action.help.strip():
            help_text = self._expand_help(action)
            if help_text:
                help_lines = self._split_lines(help_text, help_width)
                parts.append(f"{get_indented_string(help_lines[0], indent_first)}\n")
                parts.extend(
                    [
                        f"{get_indented_string(line, help_position)}\n"
                        for line in help_lines[1:]
                    ]
                )

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith("\n"):
            parts.append("\n")

        # if there are any sub-actions, add their help as well
        parts.extend(
            [
                self._format_action(subaction)
                for subaction in self._iter_indented_subactions(action)
            ]
        )

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action: Action) -> str:
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar

        # if the Optional doesn't take a value, format is:
        #    -s, --long
        if action.nargs == 0:
            return ", ".join(action.option_strings)

        # if the Optional takes a value, format is:
        #    -s, --long ARGS
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return f"{', '.join(action.option_strings)} {args_string}"

    def _metavar_formatter(
        self, action: Action, default_metavar: str
    ) -> Callable[[int], tuple[str, ...]]:
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            choice_str = ",".join([str(choice) for choice in action.choices])
            result = f"{{{choice_str}}}"
        else:
            result = default_metavar

        def format(tuple_size: int) -> tuple[str, ...]:
            if isinstance(result, tuple):
                return result

            return (result,) * tuple_size

        return format

    # TODO: refactor this shit
    def _format_args(self, action: Action, default_metavar: str) -> str:
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = "%s" % get_metavar(1)
        elif action.nargs == NArgsEnum.OPTIONAL:
            result = "[%s]" % get_metavar(1)
        elif action.nargs == NArgsEnum.ZERO_OR_MORE:
            metavar = get_metavar(1)
            if len(metavar) == 2:
                result = "[%s [%s ...]]" % metavar  # noqa: UP031
            else:
                result = "[%s ...]" % metavar
        elif action.nargs == NArgsEnum.ONE_OR_MORE:
            result = "%s [%s ...]" % get_metavar(2)  # noqa: UP031
        elif action.nargs == NArgsEnum.REMAINDER:
            result = "..."
        elif action.nargs == NArgsEnum.PARSER:
            result = "%s ..." % get_metavar(1)
        elif action.nargs == SUPPRESS:
            result = ""
        else:
            try:
                formats = ["%s"] * action.nargs
            except TypeError:
                raise ValueError("invalid nargs value") from None
            result = " ".join(formats) % get_metavar(action.nargs)
        return result

    # TODO: list variables that can be used in action help, refactor
    def _expand_help(self, action: Action) -> str:
        params = {"prog": self._prog}
        params.update(vars(action))
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], "__name__"):
                params[name] = params[name].__name__
        if params.get("choices") is not None:
            choices_str = ", ".join([str(c) for c in params["choices"]])
            params["choices"] = choices_str
        return self._get_help_string(action).format_map(params)

    def _iter_indented_subactions(self, action: Action) -> Iterator[Action]:
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            yield from get_subactions()
            self._dedent()

    def _split_lines(self, text: str, width: int) -> list[str]:
        text = self._whitespace_matcher.sub(" ", text).strip()
        # The textwrap module is used only for formatting help.
        # Delay its import for speeding up the common usage of argparse.
        import textwrap

        return textwrap.wrap(text, width)

    def _fill_text(self, text: str, width: int, indent: int) -> str:
        text = self._whitespace_matcher.sub(" ", text).strip()
        import textwrap

        return textwrap.fill(
            text, width, initial_indent=" " * indent, subsequent_indent=" " * indent
        )

    def _get_help_string(self, action: Action) -> str:
        return action.help

    def _get_default_metavar_for_optional(self, action: Action) -> str:
        return action.dest.upper()

    def _get_default_metavar_for_positional(self, action: Action) -> str:
        return action.dest


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text: str, width: int, indent: int) -> str:
        return "".join(indent * " " + line for line in text.splitlines(keepends=True))


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text: str, width: int) -> list[str]:
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action: Action) -> str:
        """
        Add the default value to the option help message.

        ArgumentDefaultsHelpFormatter and BooleanOptionalAction when it isn't
        already present. This code will do that, detecting cornercases to
        prevent duplicates or cases where it wouldn't make sense to the end
        user.
        """
        help = action.help

        if "{default}" not in help and action.default is not SUPPRESS:
            defaulting_nargs = [NArgsEnum.OPTIONAL, NArgsEnum.ZERO_OR_MORE]
            if action.option_strings or action.nargs in defaulting_nargs:
                help += " (default: {default})"
        return help


class MetavarTypeHelpFormatter(HelpFormatter):
    """Help message formatter which uses the argument 'type' as the default
    metavar value (instead of the argument 'dest')

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_default_metavar_for_optional(self, action: Action) -> str:
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action: Action) -> str:
        return action.type.__name__
