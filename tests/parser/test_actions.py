# ================================
# Actions returned by add_argument
# ================================
from __future__ import annotations

from unittest import TestCase

from cleo.parser.parser import ArgumentParser


class TestActionsReturned(TestCase):
    def test_dest(self):
        parser = ArgumentParser()
        action = parser.add_argument("--foo")
        self.assertEqual(action.dest, "foo")
        action = parser.add_argument("-b", "--bar")
        self.assertEqual(action.dest, "bar")
        action = parser.add_argument("-x", "-y")
        self.assertEqual(action.dest, "x")

    def test_misc(self):
        parser = ArgumentParser()
        action = parser.add_argument(
            "--foo",
            nargs="?",
            const=42,
            default=84,
            type=int,
            choices=[1, 2],
            help="FOO",
            metavar="BAR",
            dest="baz",
        )
        self.assertEqual(action.nargs, "?")
        self.assertEqual(action.const, 42)
        self.assertEqual(action.default, 84)
        self.assertEqual(action.type, int)
        self.assertEqual(action.choices, [1, 2])
        self.assertEqual(action.help, "FOO")
        self.assertEqual(action.metavar, "BAR")
        self.assertEqual(action.dest, "baz")
