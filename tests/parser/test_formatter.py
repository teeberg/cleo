from __future__ import annotations

import sys
import textwrap

from unittest import TestCase

from cleo.parser.parser import SUPPRESS
from cleo.parser.parser import ArgumentDefaultsHelpFormatter
from cleo.parser.parser import ArgumentParser
from cleo.parser.parser import BooleanOptionalAction
from cleo.parser.parser import MetavarTypeHelpFormatter
from cleo.parser.parser import RawDescriptionHelpFormatter
from cleo.parser.parser import RawTextHelpFormatter
from tests.parser.helpers import EnvironmentVarGuard
from tests.parser.helpers import Sig
from tests.parser.helpers import StdIOBuffer


# =====================
# Help formatting tests
# =====================


class HelpFormattingMetaclass(type):
    def __init__(cls, name, bases, bodydict):
        if name == "HelpTestCase":
            return

        class AddTests:
            def __init__(self, test_class, func_suffix, std_name):
                self.func_suffix = func_suffix
                self.std_name = std_name

                for test_func in [
                    self.test_format,
                    self.test_print,
                    self.test_print_file,
                ]:
                    test_name = f"{test_func.__name__}_{func_suffix}"

                    def test_wrapper(self, test_func=test_func):
                        test_func(self)

                    try:
                        test_wrapper.__name__ = test_name
                    except TypeError:
                        pass
                    setattr(test_class, test_name, test_wrapper)

            def _get_parser(self, tester):
                parser = ArgumentParser(
                    *tester.parser_signature.args, **tester.parser_signature.kwargs
                )
                for argument_sig in getattr(tester, "argument_signatures", []):
                    parser.add_argument(*argument_sig.args, **argument_sig.kwargs)
                group_sigs = getattr(tester, "argument_group_signatures", [])
                for group_sig, argument_sigs in group_sigs:
                    group = parser.add_argument_group(
                        *group_sig.args, **group_sig.kwargs
                    )
                    for argument_sig in argument_sigs:
                        group.add_argument(*argument_sig.args, **argument_sig.kwargs)
                subparsers_sigs = getattr(tester, "subparsers_signatures", [])
                if subparsers_sigs:
                    subparsers = parser.add_subparsers()
                    for subparser_sig in subparsers_sigs:
                        subparsers.add_parser(
                            *subparser_sig.args, **subparser_sig.kwargs
                        )
                return parser

            def _test(self, tester, parser_text):
                expected_text = getattr(tester, self.func_suffix)
                expected_text = textwrap.dedent(expected_text)
                tester.maxDiff = None
                tester.assertEqual(expected_text, parser_text)

            def test_format(self, tester):
                parser = self._get_parser(tester)
                format = getattr(parser, f"format_{self.func_suffix}")
                self._test(tester, format())

            def test_print(self, tester):
                parser = self._get_parser(tester)
                print_ = getattr(parser, f"print_{self.func_suffix}")
                old_stream = getattr(sys, self.std_name)
                setattr(sys, self.std_name, StdIOBuffer())
                try:
                    print_()
                    parser_text = getattr(sys, self.std_name).getvalue()
                finally:
                    setattr(sys, self.std_name, old_stream)
                self._test(tester, parser_text)

            def test_print_file(self, tester):
                parser = self._get_parser(tester)
                print_ = getattr(parser, f"print_{self.func_suffix}")
                sfile = StdIOBuffer()
                print_(sfile)
                parser_text = sfile.getvalue()
                self._test(tester, parser_text)

        # add tests for {format,print}_{usage,help}
        for func_suffix, std_name in [("usage", "stdout"), ("help", "stdout")]:
            AddTests(cls, func_suffix, std_name)


bases = (TestCase,)
HelpTestCase = HelpFormattingMetaclass("HelpTestCase", bases, {})


class TestHelpBiggerOptionals(HelpTestCase):
    """Make sure that argument help aligns when options are longer"""

    parser_signature = Sig(prog="PROG", description="DESCRIPTION", epilog="EPILOG")
    argument_signatures = [
        Sig("-v", "--version", action="version", version="0.1"),
        Sig("-x", action="store_true", help="X HELP"),
        Sig("--y", help="Y HELP"),
        Sig("foo", help="FOO HELP"),
        Sig("bar", help="BAR HELP"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-v] [-x] [--y Y] foo bar
        """
    help = (
        usage
        + """\

        DESCRIPTION

        positional arguments:
          foo            FOO HELP
          bar            BAR HELP

        options:
          -h, --help     show this help message and exit
          -v, --version  show program's version number and exit
          -x             X HELP
          --y Y          Y HELP

        EPILOG
    """
    )
    version = """\
        0.1
        """


class TestShortColumns(HelpTestCase):
    """Test extremely small number of columns.

    TestCase prevents "COLUMNS" from being too small in the tests themselves,
    but we don't want any exceptions thrown in such cases. Only ugly representation.
    """

    def setUp(self):
        env = EnvironmentVarGuard()
        env.set("COLUMNS", "15")
        self.addCleanup(env.__exit__)

    parser_signature = TestHelpBiggerOptionals.parser_signature
    argument_signatures = TestHelpBiggerOptionals.argument_signatures
    argument_group_signatures = TestHelpBiggerOptionals.argument_group_signatures
    usage = """\
        usage: PROG
               [-h]
               [-v]
               [-x]
               [--y Y]
               foo
               bar
        """
    help = (
        usage
        + """\

        DESCRIPTION

        positional arguments:
          foo
            FOO HELP
          bar
            BAR HELP

        options:
          -h, --help
            show this
            help
            message and
            exit
          -v, --version
            show
            program's
            version
            number and
            exit
          -x
            X HELP
          --y Y
            Y HELP

        EPILOG
    """
    )
    version = TestHelpBiggerOptionals.version


class TestHelpBiggerOptionalGroups(HelpTestCase):
    """Make sure that argument help aligns when options are longer"""

    parser_signature = Sig(prog="PROG", description="DESCRIPTION", epilog="EPILOG")
    argument_signatures = [
        Sig("-v", "--version", action="version", version="0.1"),
        Sig("-x", action="store_true", help="X HELP"),
        Sig("--y", help="Y HELP"),
        Sig("foo", help="FOO HELP"),
        Sig("bar", help="BAR HELP"),
    ]
    argument_group_signatures = [
        (
            Sig("GROUP TITLE", description="GROUP DESCRIPTION"),
            [Sig("baz", help="BAZ HELP"), Sig("-z", nargs="+", help="Z HELP")],
        ),
    ]
    usage = """\
        usage: PROG [-h] [-v] [-x] [--y Y] [-z Z [Z ...]] foo bar baz
        """
    help = (
        usage
        + """\

        DESCRIPTION

        positional arguments:
          foo            FOO HELP
          bar            BAR HELP

        options:
          -h, --help     show this help message and exit
          -v, --version  show program's version number and exit
          -x             X HELP
          --y Y          Y HELP

        GROUP TITLE:
          GROUP DESCRIPTION

          baz            BAZ HELP
          -z Z [Z ...]   Z HELP

        EPILOG
    """
    )
    version = """\
        0.1
        """


class TestHelpBiggerPositionals(HelpTestCase):
    """Make sure that help aligns when arguments are longer"""

    parser_signature = Sig(usage="USAGE", description="DESCRIPTION")
    argument_signatures = [
        Sig("-x", action="store_true", help="X HELP"),
        Sig("--y", help="Y HELP"),
        Sig("ekiekiekifekang", help="EKI HELP"),
        Sig("bar", help="BAR HELP"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: USAGE
        """
    help = (
        usage
        + """\

        DESCRIPTION

        positional arguments:
          ekiekiekifekang  EKI HELP
          bar              BAR HELP

        options:
          -h, --help       show this help message and exit
          -x               X HELP
          --y Y            Y HELP
        """
    )

    version = ""


class TestHelpReformatting(HelpTestCase):
    """Make sure that text after short names starts on the first line"""

    parser_signature = Sig(
        prog="PROG",
        description="   oddly    formatted\n"
        "description\n"
        "\n"
        "that is so long that it should go onto multiple "
        "lines when wrapped",
    )
    argument_signatures = [
        Sig("-x", metavar="XX", help="oddly\n" "    formatted -x help"),
        Sig("y", metavar="yyy", help="normal y help"),
    ]
    argument_group_signatures = [
        (
            Sig(
                "title",
                description="\n" "    oddly formatted group\n" "\n" "description",
            ),
            [
                Sig(
                    "-a",
                    action="store_true",
                    help=" oddly \n"
                    "formatted    -a  help  \n"
                    "    again, so long that it should be wrapped over "
                    "multiple lines",
                )
            ],
        ),
    ]
    usage = """\
        usage: PROG [-h] [-x XX] [-a] yyy
        """
    help = (
        usage
        + """\

        oddly formatted description that is so long that it should go onto \
multiple
        lines when wrapped

        positional arguments:
          yyy         normal y help

        options:
          -h, --help  show this help message and exit
          -x XX       oddly formatted -x help

        title:
          oddly formatted group description

          -a          oddly formatted -a help again, so long that it should \
be wrapped
                      over multiple lines
        """
    )
    version = ""


class TestHelpWrappingShortNames(HelpTestCase):
    """Make sure that text after short names starts on the first line"""

    parser_signature = Sig(prog="PROG", description="D\nD" * 30)
    argument_signatures = [
        Sig("-x", metavar="XX", help="XHH HX" * 20),
        Sig("y", metavar="yyy", help="YH YH" * 20),
    ]
    argument_group_signatures = [
        (Sig("ALPHAS"), [Sig("-a", action="store_true", help="AHHH HHA" * 10)]),
    ]
    usage = """\
        usage: PROG [-h] [-x XX] [-a] yyy
        """
    help = (
        usage
        + """\

        D DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD \
DD DD DD
        DD DD DD DD D

        positional arguments:
          yyy         YH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH \
YHYH YHYH
                      YHYH YHYH YHYH YHYH YHYH YHYH YHYH YH

        options:
          -h, --help  show this help message and exit
          -x XX       XHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH \
HXXHH HXXHH
                      HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HXXHH HX

        ALPHAS:
          -a          AHHH HHAAHHH HHAAHHH HHAAHHH HHAAHHH HHAAHHH HHAAHHH \
HHAAHHH
                      HHAAHHH HHAAHHH HHA
        """
    )
    version = ""


class TestHelpWrappingLongNames(HelpTestCase):
    """Make sure that text after long names starts on the next line"""

    parser_signature = Sig(usage="USAGE", description="D D" * 30)
    argument_signatures = [
        Sig("-v", "--version", action="version", version="V V" * 30),
        Sig("-x", metavar="X" * 25, help="XH XH" * 20),
        Sig("y", metavar="y" * 25, help="YH YH" * 20),
    ]
    argument_group_signatures = [
        (
            Sig("ALPHAS"),
            [
                Sig("-a", metavar="A" * 25, help="AH AH" * 20),
                Sig("z", metavar="z" * 25, help="ZH ZH" * 20),
            ],
        ),
    ]
    usage = """\
        usage: USAGE
        """
    help = (
        usage
        + """\

        D DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD \
DD DD DD
        DD DD DD DD D

        positional arguments:
          yyyyyyyyyyyyyyyyyyyyyyyyy
                                YH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH \
YHYH YHYH
                                YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YHYH YH

        options:
          -h, --help            show this help message and exit
          -v, --version         show program's version number and exit
          -x XXXXXXXXXXXXXXXXXXXXXXXXX
                                XH XHXH XHXH XHXH XHXH XHXH XHXH XHXH XHXH \
XHXH XHXH
                                XHXH XHXH XHXH XHXH XHXH XHXH XHXH XHXH XHXH XH

        ALPHAS:
          -a AAAAAAAAAAAAAAAAAAAAAAAAA
                                AH AHAH AHAH AHAH AHAH AHAH AHAH AHAH AHAH \
AHAH AHAH
                                AHAH AHAH AHAH AHAH AHAH AHAH AHAH AHAH AHAH AH
          zzzzzzzzzzzzzzzzzzzzzzzzz
                                ZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH \
ZHZH ZHZH
                                ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZHZH ZH
        """
    )
    version = """\
        V VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV VV \
VV VV VV
        VV VV VV VV V
        """


class TestHelpUsage(HelpTestCase):
    """Test basic usage messages"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-w", nargs="+", help="w"),
        Sig("-x", nargs="*", help="x"),
        Sig("a", help="a"),
        Sig("b", help="b", nargs=2),
        Sig("c", help="c", nargs="?"),
        Sig("--foo", help="Whether to foo", action=BooleanOptionalAction),
        Sig(
            "--bar",
            help="Whether to bar",
            default=True,
            action=BooleanOptionalAction,
        ),
        Sig("-f", "--foobar", "--barfoo", action=BooleanOptionalAction),
        Sig(
            "--bazz",
            action=BooleanOptionalAction,
            default=SUPPRESS,
            help="Bazz!",
        ),
    ]
    argument_group_signatures = [
        (
            Sig("group"),
            [
                Sig("-y", nargs="?", help="y"),
                Sig("-z", nargs=3, help="z"),
                Sig("d", help="d", nargs="*"),
                Sig("e", help="e", nargs="+"),
            ],
        )
    ]
    usage = """\
        usage: PROG [-h] [-w W [W ...]] [-x [X ...]] [--foo | --no-foo]
                    [--bar | --no-bar]
                    [-f | --foobar | --no-foobar | --barfoo | --no-barfoo]
                    [--bazz | --no-bazz] [-y [Y]] [-z Z Z Z]
                    a b b [c] [d ...] e [e ...]
        """
    help = (
        usage
        + """\

        positional arguments:
          a                     a
          b                     b
          c                     c

        options:
          -h, --help            show this help message and exit
          -w W [W ...]          w
          -x [X ...]            x
          --foo, --no-foo       Whether to foo
          --bar, --no-bar       Whether to bar
          -f, --foobar, --no-foobar, --barfoo, --no-barfoo
          --bazz, --no-bazz     Bazz!

        group:
          -y [Y]                y
          -z Z Z Z              z
          d                     d
          e                     e
        """
    )
    version = ""


class TestHelpUsageWithParentheses(HelpTestCase):
    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("positional", metavar="(example) positional"),
        Sig("-p", "--optional", metavar="{1 (option A), 2 (option B)}"),
    ]

    usage = """\
        usage: PROG [-h] [-p {1 (option A), 2 (option B)}] (example) positional
        """
    help = (
        usage
        + """\

        positional arguments:
          (example) positional

        options:
          -h, --help            show this help message and exit
          -p, --optional {1 (option A), 2 (option B)}
        """
    )
    version = ""


class TestHelpOnlyUserGroups(HelpTestCase):
    """Test basic usage messages"""

    parser_signature = Sig(prog="PROG", add_help=False)
    argument_signatures = []
    argument_group_signatures = [
        (
            Sig("xxxx"),
            [
                Sig("-x", help="x"),
                Sig("a", help="a"),
            ],
        ),
        (
            Sig("yyyy"),
            [
                Sig("b", help="b"),
                Sig("-y", help="y"),
            ],
        ),
    ]
    usage = """\
        usage: PROG [-x X] [-y Y] a b
        """
    help = (
        usage
        + """\

        xxxx:
          -x X  x
          a     a

        yyyy:
          b     b
          -y Y  y
        """
    )
    version = ""


class TestHelpUsageLongProg(HelpTestCase):
    """Test usage messages where the prog is long"""

    parser_signature = Sig(prog="P" * 60)
    argument_signatures = [
        Sig("-w", metavar="W"),
        Sig("-x", metavar="X"),
        Sig("a"),
        Sig("b"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
               [-h] [-w W] [-x X] a b
        """
    help = (
        usage
        + """\

        positional arguments:
          a
          b

        options:
          -h, --help  show this help message and exit
          -w W
          -x X
        """
    )
    version = ""


class TestHelpUsageLongProgOptionsWrap(HelpTestCase):
    """Test usage messages where the prog is long and the optionals wrap"""

    parser_signature = Sig(prog="P" * 60)
    argument_signatures = [
        Sig("-w", metavar="W" * 25),
        Sig("-x", metavar="X" * 25),
        Sig("-y", metavar="Y" * 25),
        Sig("-z", metavar="Z" * 25),
        Sig("a"),
        Sig("b"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
               [-h] [-w WWWWWWWWWWWWWWWWWWWWWWWWW] \
[-x XXXXXXXXXXXXXXXXXXXXXXXXX]
               [-y YYYYYYYYYYYYYYYYYYYYYYYYY] [-z ZZZZZZZZZZZZZZZZZZZZZZZZZ]
               a b
        """
    help = (
        usage
        + """\

        positional arguments:
          a
          b

        options:
          -h, --help            show this help message and exit
          -w WWWWWWWWWWWWWWWWWWWWWWWWW
          -x XXXXXXXXXXXXXXXXXXXXXXXXX
          -y YYYYYYYYYYYYYYYYYYYYYYYYY
          -z ZZZZZZZZZZZZZZZZZZZZZZZZZ
        """
    )
    version = ""


class TestHelpUsageLongProgPositionalsWrap(HelpTestCase):
    """Test usage messages where the prog is long and the positionals wrap"""

    parser_signature = Sig(prog="P" * 60, add_help=False)
    argument_signatures = [
        Sig("a" * 25),
        Sig("b" * 25),
        Sig("c" * 25),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
               aaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbb
               ccccccccccccccccccccccccc
        """
    help = (
        usage
        + """\

        positional arguments:
          aaaaaaaaaaaaaaaaaaaaaaaaa
          bbbbbbbbbbbbbbbbbbbbbbbbb
          ccccccccccccccccccccccccc
        """
    )
    version = ""


class TestHelpUsageOptionalsWrap(HelpTestCase):
    """Test usage messages where the optionals wrap"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-w", metavar="W" * 25),
        Sig("-x", metavar="X" * 25),
        Sig("-y", metavar="Y" * 25),
        Sig("-z", metavar="Z" * 25),
        Sig("a"),
        Sig("b"),
        Sig("c"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-w WWWWWWWWWWWWWWWWWWWWWWWWW] \
[-x XXXXXXXXXXXXXXXXXXXXXXXXX]
                    [-y YYYYYYYYYYYYYYYYYYYYYYYYY] \
[-z ZZZZZZZZZZZZZZZZZZZZZZZZZ]
                    a b c
        """
    help = (
        usage
        + """\

        positional arguments:
          a
          b
          c

        options:
          -h, --help            show this help message and exit
          -w WWWWWWWWWWWWWWWWWWWWWWWWW
          -x XXXXXXXXXXXXXXXXXXXXXXXXX
          -y YYYYYYYYYYYYYYYYYYYYYYYYY
          -z ZZZZZZZZZZZZZZZZZZZZZZZZZ
        """
    )
    version = ""


class TestHelpUsagePositionalsWrap(HelpTestCase):
    """Test usage messages where the positionals wrap"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-x"),
        Sig("-y"),
        Sig("-z"),
        Sig("a" * 25),
        Sig("b" * 25),
        Sig("c" * 25),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-x X] [-y Y] [-z Z]
                    aaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbb
                    ccccccccccccccccccccccccc
        """
    help = (
        usage
        + """\

        positional arguments:
          aaaaaaaaaaaaaaaaaaaaaaaaa
          bbbbbbbbbbbbbbbbbbbbbbbbb
          ccccccccccccccccccccccccc

        options:
          -h, --help            show this help message and exit
          -x X
          -y Y
          -z Z
        """
    )
    version = ""


class TestHelpUsageOptionalsPositionalsWrap(HelpTestCase):
    """Test usage messages where the optionals and positionals wrap"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-x", metavar="X" * 25),
        Sig("-y", metavar="Y" * 25),
        Sig("-z", metavar="Z" * 25),
        Sig("a" * 25),
        Sig("b" * 25),
        Sig("c" * 25),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-x XXXXXXXXXXXXXXXXXXXXXXXXX] \
[-y YYYYYYYYYYYYYYYYYYYYYYYYY]
                    [-z ZZZZZZZZZZZZZZZZZZZZZZZZZ]
                    aaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbb
                    ccccccccccccccccccccccccc
        """
    help = (
        usage
        + """\

        positional arguments:
          aaaaaaaaaaaaaaaaaaaaaaaaa
          bbbbbbbbbbbbbbbbbbbbbbbbb
          ccccccccccccccccccccccccc

        options:
          -h, --help            show this help message and exit
          -x XXXXXXXXXXXXXXXXXXXXXXXXX
          -y YYYYYYYYYYYYYYYYYYYYYYYYY
          -z ZZZZZZZZZZZZZZZZZZZZZZZZZ
        """
    )
    version = ""


class TestHelpUsageOptionalsOnlyWrap(HelpTestCase):
    """Test usage messages where there are only optionals and they wrap"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-x", metavar="X" * 25),
        Sig("-y", metavar="Y" * 25),
        Sig("-z", metavar="Z" * 25),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-x XXXXXXXXXXXXXXXXXXXXXXXXX] \
[-y YYYYYYYYYYYYYYYYYYYYYYYYY]
                    [-z ZZZZZZZZZZZZZZZZZZZZZZZZZ]
        """
    help = (
        usage
        + """\

        options:
          -h, --help            show this help message and exit
          -x XXXXXXXXXXXXXXXXXXXXXXXXX
          -y YYYYYYYYYYYYYYYYYYYYYYYYY
          -z ZZZZZZZZZZZZZZZZZZZZZZZZZ
        """
    )
    version = ""


class TestHelpUsagePositionalsOnlyWrap(HelpTestCase):
    """Test usage messages where there are only positionals and they wrap"""

    parser_signature = Sig(prog="PROG", add_help=False)
    argument_signatures = [
        Sig("a" * 25),
        Sig("b" * 25),
        Sig("c" * 25),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG aaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbb
                    ccccccccccccccccccccccccc
        """
    help = (
        usage
        + """\

        positional arguments:
          aaaaaaaaaaaaaaaaaaaaaaaaa
          bbbbbbbbbbbbbbbbbbbbbbbbb
          ccccccccccccccccccccccccc
        """
    )
    version = ""


class TestHelpVariableExpansion(HelpTestCase):
    """Test that variables are expanded properly in help messages"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-x", type=int, help="x {prog} {default} {type} %"),
        Sig(
            "-y",
            action="store_const",
            default=42,
            const="XXX",
            help="y {prog} {default} {const}",
        ),
        Sig("--foo", choices="abc", help="foo {prog} {default} {choices}"),
        Sig(
            "--bar",
            default="baz",
            choices=[1, 2],
            metavar="BBB",
            help="bar {prog} {default} {dest}",
        ),
        Sig("spam", help="spam {prog} {default}"),
        Sig("badger", default=0.5, help="badger {prog} {default}"),
    ]
    argument_group_signatures = [
        (
            Sig("group"),
            [
                Sig("-a", help="a {prog} {default}"),
                Sig("-b", default=-1, help="b {prog} {default}"),
            ],
        )
    ]
    usage = """\
        usage: PROG [-h] [-x X] [-y] [--foo {a,b,c}] [--bar BBB] [-a A] [-b B]
                    spam badger
        """
    help = (
        usage
        + """\

        positional arguments:
          spam           spam PROG None
          badger         badger PROG 0.5

        options:
          -h, --help     show this help message and exit
          -x X           x PROG None int %
          -y             y PROG 42 XXX
          --foo {a,b,c}  foo PROG None a, b, c
          --bar BBB      bar PROG baz bar

        group:
          -a A           a PROG None
          -b B           b PROG -1
        """
    )
    version = ""


class TestHelpVariableExpansionUsageSupplied(HelpTestCase):
    """Test that variables are expanded properly when usage= is present"""

    parser_signature = Sig(prog="PROG", usage="{prog} FOO")
    argument_signatures = []
    argument_group_signatures = []
    usage = """\
        usage: PROG FOO
        """
    help = (
        usage
        + """\

        options:
          -h, --help  show this help message and exit
        """
    )
    version = ""


class TestHelpVariableExpansionNoArguments(HelpTestCase):
    """Test that variables are expanded properly with no arguments"""

    parser_signature = Sig(prog="PROG", add_help=False)
    argument_signatures = []
    argument_group_signatures = []
    usage = """\
        usage: PROG
        """
    help = usage
    version = ""


class TestHelpSuppressUsage(HelpTestCase):
    """Test that items can be suppressed in usage messages"""

    parser_signature = Sig(prog="PROG", usage=SUPPRESS)
    argument_signatures = [
        Sig("--foo", help="foo help"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = []
    help = """\
        positional arguments:
          spam        spam help

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help
        """
    usage = ""
    version = ""


class TestHelpSuppressOptional(HelpTestCase):
    """Test that optional arguments can be suppressed in help messages"""

    parser_signature = Sig(prog="PROG", add_help=False)
    argument_signatures = [
        Sig("--foo", help=SUPPRESS),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG spam
        """
    help = (
        usage
        + """\

        positional arguments:
          spam  spam help
        """
    )
    version = ""


class TestHelpSuppressOptionalGroup(HelpTestCase):
    """Test that optional groups can be suppressed in help messages"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("--foo", help="foo help"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = [
        (Sig("group"), [Sig("--bar", help=SUPPRESS)]),
    ]
    usage = """\
        usage: PROG [-h] [--foo FOO] spam
        """
    help = (
        usage
        + """\

        positional arguments:
          spam        spam help

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help
        """
    )
    version = ""


class TestHelpSuppressPositional(HelpTestCase):
    """Test that positional arguments can be suppressed in help messages"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("--foo", help="foo help"),
        Sig("spam", help=SUPPRESS),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [--foo FOO]
        """
    help = (
        usage
        + """\

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help
        """
    )
    version = ""


class TestHelpRequiredOptional(HelpTestCase):
    """Test that required options don't look optional"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("--foo", required=True, help="foo help"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] --foo FOO
        """
    help = (
        usage
        + """\

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help
        """
    )
    version = ""


class TestHelpAlternatePrefixChars(HelpTestCase):
    """Test that options display with different prefix characters"""

    parser_signature = Sig(prog="PROG", prefix_chars="^;", add_help=False)
    argument_signatures = [
        Sig("^^foo", action="store_true", help="foo help"),
        Sig(";b", ";;bar", help="bar help"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [^^foo] [;b BAR]
        """
    help = (
        usage
        + """\

        options:
          ^^foo          foo help
          ;b, ;;bar BAR  bar help
        """
    )
    version = ""


class TestHelpNoHelpOptional(HelpTestCase):
    """Test that the --help argument can be suppressed help messages"""

    parser_signature = Sig(prog="PROG", add_help=False)
    argument_signatures = [
        Sig("--foo", help="foo help"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [--foo FOO] spam
        """
    help = (
        usage
        + """\

        positional arguments:
          spam       spam help

        options:
          --foo FOO  foo help
        """
    )
    version = ""


class TestHelpNone(HelpTestCase):
    """Test that no errors occur if no help is specified"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("--foo"),
        Sig("spam"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [--foo FOO] spam
        """
    help = (
        usage
        + """\

        positional arguments:
          spam

        options:
          -h, --help  show this help message and exit
          --foo FOO
        """
    )
    version = ""


class TestHelpTupleMetavar(HelpTestCase):
    """Test specifying metavar as a tuple"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-w", help="w", nargs="+", metavar=("W1", "W2")),
        Sig("-x", help="x", nargs="*", metavar=("X1", "X2")),
        Sig("-y", help="y", nargs=3, metavar=("Y1", "Y2", "Y3")),
        Sig("-z", help="z", nargs="?", metavar=("Z1",)),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-w W1 [W2 ...]] [-x [X1 [X2 ...]]] [-y Y1 Y2 Y3] \
[-z [Z1]]
        """
    help = (
        usage
        + """\

        options:
          -h, --help        show this help message and exit
          -w W1 [W2 ...]    w
          -x [X1 [X2 ...]]  x
          -y Y1 Y2 Y3       y
          -z [Z1]           z
        """
    )
    version = ""


class TestHelpRawText(HelpTestCase):
    """Test the RawTextHelpFormatter"""

    parser_signature = Sig(
        prog="PROG",
        formatter_class=RawTextHelpFormatter,
        description="Keep the formatting\n"
        "    exactly as it is written\n"
        "\n"
        "here\n",
    )

    argument_signatures = [
        Sig("--foo", help="    foo help should also\n" "appear as given here"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = [
        (
            Sig(
                "title",
                description="    This text\n"
                "  should be indented\n"
                "    exactly like it is here\n",
            ),
            [Sig("--bar", help="bar help")],
        ),
    ]
    usage = """\
        usage: PROG [-h] [--foo FOO] [--bar BAR] spam
        """
    help = (
        usage
        + """\

        Keep the formatting
            exactly as it is written

        here

        positional arguments:
          spam        spam help

        options:
          -h, --help  show this help message and exit
          --foo FOO       foo help should also
                      appear as given here

        title:
              This text
            should be indented
              exactly like it is here

          --bar BAR   bar help
        """
    )
    version = ""


class TestHelpRawDescription(HelpTestCase):
    """Test the RawTextHelpFormatter"""

    parser_signature = Sig(
        prog="PROG",
        formatter_class=RawDescriptionHelpFormatter,
        description="Keep the formatting\n"
        "    exactly as it is written\n"
        "\n"
        "here\n",
    )

    argument_signatures = [
        Sig("--foo", help="  foo help should not\n" "    retain this odd formatting"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = [
        (
            Sig(
                "title",
                description="    This text\n"
                "  should be indented\n"
                "    exactly like it is here\n",
            ),
            [Sig("--bar", help="bar help")],
        ),
    ]
    usage = """\
        usage: PROG [-h] [--foo FOO] [--bar BAR] spam
        """
    help = (
        usage
        + """\

        Keep the formatting
            exactly as it is written

        here

        positional arguments:
          spam        spam help

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help should not retain this odd formatting

        title:
              This text
            should be indented
              exactly like it is here

          --bar BAR   bar help
        """
    )
    version = ""


class TestHelpArgumentDefaults(HelpTestCase):
    """Test the ArgumentDefaultsHelpFormatter"""

    parser_signature = Sig(
        prog="PROG",
        formatter_class=ArgumentDefaultsHelpFormatter,
        description="description",
    )

    argument_signatures = [
        Sig("--foo", help="foo help - oh and by the way, {default}"),
        Sig("--bar", action="store_true", help="bar help"),
        Sig(
            "--taz",
            action=BooleanOptionalAction,
            help="Whether to taz it",
            default=True,
        ),
        Sig(
            "--corge",
            action=BooleanOptionalAction,
            help="Whether to corge it",
            default=SUPPRESS,
        ),
        Sig("--quux", help="Set the quux", default=42),
        Sig("spam", help="spam help"),
        Sig("badger", nargs="?", default="wooden", help="badger help"),
    ]
    argument_group_signatures = [
        (
            Sig("title", description="description"),
            [Sig("--baz", type=int, default=42, help="baz help")],
        ),
    ]
    usage = """\
        usage: PROG [-h] [--foo FOO] [--bar] [--taz | --no-taz] [--corge | --no-corge]
                    [--quux QUUX] [--baz BAZ]
                    spam [badger]
        """
    help = (
        usage
        + """\

        description

        positional arguments:
          spam                 spam help
          badger               badger help (default: wooden)

        options:
          -h, --help           show this help message and exit
          --foo FOO            foo help - oh and by the way, None
          --bar                bar help (default: False)
          --taz, --no-taz      Whether to taz it (default: True)
          --corge, --no-corge  Whether to corge it
          --quux QUUX          Set the quux (default: 42)

        title:
          description

          --baz BAZ            baz help (default: 42)
        """
    )
    version = ""


class TestHelpVersionAction(HelpTestCase):
    """Test the default help for the version action"""

    parser_signature = Sig(prog="PROG", description="description")
    argument_signatures = [Sig("-V", "--version", action="version", version="3.6")]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-V]
        """
    help = (
        usage
        + """\

        description

        options:
          -h, --help     show this help message and exit
          -V, --version  show program's version number and exit
        """
    )
    version = ""


class TestHelpVersionActionSuppress(HelpTestCase):
    """Test that the --version argument can be suppressed in help messages"""

    parser_signature = Sig(prog="PROG")
    argument_signatures = [
        Sig("-v", "--version", action="version", version="1.0", help=SUPPRESS),
        Sig("--foo", help="foo help"),
        Sig("spam", help="spam help"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [--foo FOO] spam
        """
    help = (
        usage
        + """\

        positional arguments:
          spam        spam help

        options:
          -h, --help  show this help message and exit
          --foo FOO   foo help
        """
    )


class TestHelpSubparsersOrdering(HelpTestCase):
    """Test ordering of subcommands in help matches the code"""

    parser_signature = Sig(prog="PROG", description="display some subcommands")
    argument_signatures = [Sig("-v", "--version", action="version", version="0.1")]

    subparsers_signatures = [Sig(name=name) for name in ("a", "b", "c", "d", "e")]

    usage = """\
        usage: PROG [-h] [-v] {a,b,c,d,e} ...
        """

    help = (
        usage
        + """\

        display some subcommands

        positional arguments:
          {a,b,c,d,e}

        options:
          -h, --help     show this help message and exit
          -v, --version  show program's version number and exit
        """
    )

    version = """\
        0.1
        """


class TestHelpSubparsersWithHelpOrdering(HelpTestCase):
    """Test ordering of subcommands in help matches the code"""

    parser_signature = Sig(prog="PROG", description="display some subcommands")
    argument_signatures = [Sig("-v", "--version", action="version", version="0.1")]

    subcommand_data = (
        ("a", "a subcommand help"),
        ("b", "b subcommand help"),
        ("c", "c subcommand help"),
        ("d", "d subcommand help"),
        ("e", "e subcommand help"),
    )

    subparsers_signatures = [
        Sig(name=name, help=help) for name, help in subcommand_data
    ]

    usage = """\
        usage: PROG [-h] [-v] {a,b,c,d,e} ...
        """

    help = (
        usage
        + """\

        display some subcommands

        positional arguments:
          {a,b,c,d,e}
            a            a subcommand help
            b            b subcommand help
            c            c subcommand help
            d            d subcommand help
            e            e subcommand help

        options:
          -h, --help     show this help message and exit
          -v, --version  show program's version number and exit
        """
    )

    version = """\
        0.1
        """


class TestHelpMetavarTypeFormatter(HelpTestCase):
    def custom_type(string):
        return string

    parser_signature = Sig(
        prog="PROG",
        description="description",
        formatter_class=MetavarTypeHelpFormatter,
    )
    argument_signatures = [
        Sig("a", type=int),
        Sig("-b", type=custom_type),
        Sig("-c", type=float, metavar="SOME FLOAT"),
    ]
    argument_group_signatures = []
    usage = """\
        usage: PROG [-h] [-b custom_type] [-c SOME FLOAT] int
        """
    help = (
        usage
        + """\

        description

        positional arguments:
          int

        options:
          -h, --help      show this help message and exit
          -b custom_type
          -c SOME FLOAT
        """
    )
    version = ""


# =====================================
# Optional/Positional constructor tests
# =====================================


class TestInvalidArgumentConstructors(TestCase):
    """Test a bunch of invalid Argument constructors"""

    def assertTypeError(self, *args, **kwargs):
        parser = ArgumentParser()
        self.assertRaises(TypeError, parser.add_argument, *args, **kwargs)

    def assertValueError(self, *args, **kwargs):
        parser = ArgumentParser()
        self.assertRaises(ValueError, parser.add_argument, *args, **kwargs)

    def test_invalid_keyword_arguments(self):
        self.assertTypeError("-x", bar=None)
        self.assertTypeError("-y", callback="foo")
        self.assertTypeError("-y", callback_args=())
        self.assertTypeError("-y", callback_kwargs={})

    def test_missing_destination(self):
        self.assertTypeError()
        for action in ["append", "store"]:
            self.assertTypeError(action=action)

    def test_invalid_option_strings(self):
        self.assertValueError("--")
        self.assertValueError("---")

    def test_invalid_prefix(self):
        self.assertValueError("--foo", "+foo")

    def test_invalid_type(self):
        self.assertValueError("--foo", type="int")
        self.assertValueError("--foo", type=(int, float))

    def test_invalid_action(self):
        self.assertValueError("-x", action="foo")
        self.assertValueError("foo", action="baz")
        self.assertValueError("--foo", action=("store", "append"))
        parser = ArgumentParser()
        with self.assertRaises(ValueError) as cm:
            parser.add_argument("--foo", action="store-true")
        self.assertIn("unknown action", str(cm.exception))

    def test_multiple_dest(self):
        parser = ArgumentParser()
        parser.add_argument(dest="foo")
        with self.assertRaises(ValueError) as cm:
            parser.add_argument("bar", dest="baz")
        self.assertIn("dest supplied twice for positional argument", str(cm.exception))

    def test_no_argument_actions(self):
        for action in [
            "store_const",
            "store_true",
            "store_false",
            "append_const",
            "count",
        ]:
            for attrs in [dict(type=int), dict(nargs="+"), dict(choices="ab")]:
                self.assertTypeError("-x", action=action, **attrs)

    def test_no_argument_no_const_actions(self):
        # options with zero arguments
        for action in ["store_true", "store_false", "count"]:
            # const is always disallowed
            self.assertTypeError("-x", const="foo", action=action)

            # nargs is always disallowed
            self.assertTypeError("-x", nargs="*", action=action)

    def test_more_than_one_argument_actions(self):
        for action in ["store", "append"]:
            # nargs=0 is disallowed
            self.assertValueError("-x", nargs=0, action=action)
            self.assertValueError("spam", nargs=0, action=action)

            # const is disallowed with non-optional arguments
            for nargs in [1, "*", "+"]:
                self.assertValueError("-x", const="foo", nargs=nargs, action=action)
                self.assertValueError("spam", const="foo", nargs=nargs, action=action)

    def test_required_const_actions(self):
        for action in ["store_const", "append_const"]:
            # nargs is always disallowed
            self.assertTypeError("-x", nargs="+", action=action)

    def test_parsers_action_missing_params(self):
        self.assertTypeError("command", action="parsers")
        self.assertTypeError("command", action="parsers", prog="PROG")
        self.assertTypeError("command", action="parsers", parser_class=ArgumentParser)

    def test_version_missing_params(self):
        self.assertTypeError("command", action="version")

    def test_required_positional(self):
        self.assertTypeError("foo", required=True)

    def test_user_defined_action(self):
        class Success(Exception):
            pass

        class Action:
            def __init__(self, option_strings, dest, const, default, required=False):
                if dest == "spam":
                    if const is Success:
                        if default is Success:
                            raise Success()

            def __call__(self, *args, **kwargs):
                pass

        parser = ArgumentParser()
        self.assertRaises(
            Success,
            parser.add_argument,
            "--spam",
            action=Action,
            default=Success,
            const=Success,
        )
        self.assertRaises(
            Success,
            parser.add_argument,
            "spam",
            action=Action,
            default=Success,
            const=Success,
        )
