"""Tests for watchdog/probe.py: content check and classification.

Only the parts that need no network are tested: we build fake fetch
results by hand and check which status classify() gives them.
"""

import unittest
from unittest import mock

from watchdog import probe

PAGE = '<html><body><ul><li class="menu-item">Pizza</li></ul></body></html>'


def fake_fetch(status_code=200, elapsed_ms=100, html=PAGE, error=None):
    """Return a dict shaped like the result of probe.fetch()."""
    return {"status_code": status_code, "elapsed_ms": elapsed_ms,
            "html": html, "error": error}


class HasExpectedContentTests(unittest.TestCase):
    """has_expected_content: CSS selectors on a small page."""

    def test_match_and_no_match(self):
        self.assertTrue(probe.has_expected_content(PAGE, ".menu-item"))
        self.assertFalse(probe.has_expected_content(PAGE, ".product"))

    def test_invalid_selector_is_value_error(self):
        with self.assertRaises(ValueError):
            probe.has_expected_content(PAGE, "div[")


class ClassifyTests(unittest.TestCase):
    """classify: every status and the order of the checks."""

    def status_of(self, result, selector=".menu-item", slow_ms=2000):
        """Return only the status part of classify()."""
        return probe.classify(result, selector, slow_ms)[0]

    def test_up(self):
        self.assertEqual(probe.classify(fake_fetch(), ".menu-item", 2000), ("UP", ""))

    def test_slow(self):
        self.assertEqual(self.status_of(fake_fetch(elapsed_ms=2500)), "SLOW")

    def test_broken_when_selector_misses_or_page_empty(self):
        self.assertEqual(self.status_of(fake_fetch(), selector=".product"), "BROKEN")
        self.assertEqual(self.status_of(fake_fetch(html="   ")), "BROKEN")

    def test_broken_beats_slow(self):
        # A slow AND empty page is reported as the bigger problem: BROKEN.
        self.assertEqual(self.status_of(fake_fetch(elapsed_ms=9000, html="")), "BROKEN")

    def test_http_error(self):
        status, reason = probe.classify(fake_fetch(status_code=404), ".menu-item", 2000)
        self.assertEqual(status, "HTTP_ERROR")
        self.assertIn("404", reason)
        self.assertEqual(self.status_of(fake_fetch(status_code=503)), "HTTP_ERROR")

    def test_down_keeps_the_error_text(self):
        result = fake_fetch(status_code=None, elapsed_ms=None, html="",
                            error="timed out after 5 s")
        self.assertEqual(probe.classify(result, ".menu-item", 2000),
                         ("DOWN", "timed out after 5 s"))

    def test_invalid_selector_is_reported_not_raised(self):
        status, reason = probe.classify(fake_fetch(), "div[", 2000)
        self.assertEqual(status, "BROKEN")
        self.assertIn("config error", reason)


class CheckAllRetryTests(unittest.TestCase):
    """check_all: one retry for DOWN sites, limited by RETRY_BUDGET.

    check_site is replaced by a fake that returns prepared statuses, and the
    wait is set to 0, so no network is used and the test is instant.
    """

    def run_check_all(self, sites, statuses):
        """Run check_all where each call to check_site returns the next status."""
        answers = list(statuses)
        calls = []

        def fake_check_site(site, timeout, slow_ms):
            calls.append(site["id"])
            return {"id": site["id"], "name": site["id"], "status": answers.pop(0),
                    "reason": "timed out", "elapsed_ms": None}

        with mock.patch.object(probe, "check_site", fake_check_site), \
                mock.patch.object(probe, "RETRY_WAIT_SECONDS", 0):
            results = probe.check_all(sites, 5, 2000)
        return results, calls

    def test_hiccup_is_retried_and_recovers(self):
        results, calls = self.run_check_all([{"id": "a"}], ["DOWN", "UP"])
        self.assertEqual(calls, ["a", "a"])
        self.assertEqual(results[0]["status"], "UP")

    def test_still_down_says_retried(self):
        results, _ = self.run_check_all([{"id": "a"}], ["DOWN", "DOWN"])
        self.assertIn("retried once", results[0]["reason"])

    def test_budget_limits_retries(self):
        sites = [{"id": f"s{i}"} for i in range(probe.RETRY_BUDGET + 2)]
        # Every attempt is DOWN: only the first RETRY_BUDGET sites get a retry.
        statuses = ["DOWN"] * (len(sites) + probe.RETRY_BUDGET)
        results, calls = self.run_check_all(sites, statuses)
        self.assertEqual(len(calls), len(sites) + probe.RETRY_BUDGET)
        self.assertEqual(len(results), len(sites))


if __name__ == "__main__":
    unittest.main()
