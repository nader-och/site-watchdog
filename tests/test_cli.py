"""Tests for cli.py: argument checks, the parser and exit codes.

The exit-code tests start cli.py as a separate program (like a user would)
and only use "validate" and argument errors, so no network is used.
"""

import argparse
import os
import subprocess
import sys
import unittest

import cli

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_SITES = os.path.join("examples", "sites.example.json")


def run_cli(*arguments):
    """Run "python cli.py <arguments>" in the project folder; return the result."""
    return subprocess.run([sys.executable, "cli.py", *arguments], cwd=PROJECT_DIR,
                          capture_output=True, text=True, encoding="utf-8")


class NumberTypeTests(unittest.TestCase):
    """positive_number and positive_int: the custom argparse types."""

    def test_good_values(self):
        self.assertEqual(cli.positive_number("2.5"), 2.5)
        self.assertEqual(cli.positive_int("3"), 3)

    def test_bad_values(self):
        for bad in ["-1", "0", "abc", "nan", "inf"]:
            with self.assertRaises(argparse.ArgumentTypeError):
                cli.positive_number(bad)
        for bad in ["0", "-2", "1.5", "abc"]:
            with self.assertRaises(argparse.ArgumentTypeError):
                cli.positive_int(bad)


class ParserTests(unittest.TestCase):
    """build_parser: subcommands and defaults."""

    def test_check_defaults(self):
        args = cli.build_parser().parse_args(["check", "--sites", "s.json"])
        self.assertEqual((args.state, args.timeout, args.slow_ms), ("state.json", 5, 2000))
        self.assertFalse(args.notify)
        self.assertIs(args.handler, cli.handle_check)

    def test_watch_needs_every_and_runs(self):
        args = cli.build_parser().parse_args(
            ["watch", "--sites", "s.json", "--every", "10", "--runs", "3"])
        self.assertEqual((args.every, args.runs), (10.0, 3))


class ExitCodeTests(unittest.TestCase):
    """main: 0 on success, 1 for a bad input file, 2 for bad arguments."""

    def test_validate_example_is_ok(self):
        result = run_cli("validate", "--sites", EXAMPLE_SITES, "--allow-local")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK: 3 site(s)", result.stdout)

    def test_local_addresses_refused_without_flag(self):
        result = run_cli("validate", "--sites", EXAMPLE_SITES)
        self.assertEqual(result.returncode, 1)
        self.assertIn("--allow-local", result.stderr)

    def test_missing_file_is_exit_1(self):
        result = run_cli("validate", "--sites", "no-such-file.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error: sites file not found", result.stderr)

    def test_bad_argument_is_exit_2(self):
        result = run_cli("check", "--sites", EXAMPLE_SITES, "--timeout", "-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be greater than 0", result.stderr)


if __name__ == "__main__":
    unittest.main()
