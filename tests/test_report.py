"""Tests for watchdog/report.py: time display and table output."""

import io
import unittest
from contextlib import redirect_stdout

from watchdog import report


def printed(function, argument):
    """Call `function(argument)` and return everything it printed."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        function(argument)
    return buffer.getvalue()


class FormatSinceTests(unittest.TestCase):
    """format_since: stored UTC shown as Istanbul time."""

    def test_utc_is_shown_in_istanbul_time(self):
        # Istanbul is UTC+3, so 17:58 UTC is 20:58 in Istanbul.
        self.assertEqual(report.format_since("2026-10-27T17:58:28+00:00"), "27 Oct 20:58")

    def test_time_without_zone_is_treated_as_utc(self):
        self.assertEqual(report.format_since("2026-10-27T17:58:28"), "27 Oct 20:58")

    def test_invalid_values_show_unknown(self):
        for bad in ["yesterday", "", None, 42]:
            self.assertEqual(report.format_since(bad), "unknown")


class FormatMsTests(unittest.TestCase):
    """format_ms: milliseconds or a dash."""

    def test_values(self):
        self.assertEqual(report.format_ms(118), "118 ms")
        self.assertEqual(report.format_ms(None), report.NO_VALUE)


class TableTests(unittest.TestCase):
    """print_check_table and print_state_report: problems first."""

    def test_check_table_puts_problems_first(self):
        results = [
            {"id": "ok", "status": "UP", "reason": "", "elapsed_ms": 10},
            {"id": "dead", "status": "DOWN", "reason": "timed out", "elapsed_ms": None},
        ]
        lines = printed(report.print_check_table, results).splitlines()
        self.assertIn("dead", lines[0])
        self.assertIn("timed out", lines[0])
        self.assertIn("ok", lines[1])

    def test_state_report_shows_istanbul_time_and_name(self):
        state = {"zeytin": {"name": "مطعم الزيتون", "status": "UP",
                            "since": "2026-10-27T17:58:28+00:00", "elapsed_ms": 6}}
        text = printed(report.print_state_report, state)
        self.assertIn("27 Oct 20:58", text)
        self.assertIn("مطعم الزيتون", text)

    def test_empty_state_message(self):
        self.assertIn("No saved state yet", printed(report.print_state_report, {}))


if __name__ == "__main__":
    unittest.main()
