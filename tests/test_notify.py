"""Tests for watchdog/notify.py: topic checks and alert text.
No message is ever sent."""

import os
import unittest

from watchdog import notify


def transition(site_id, old, new, reason):
    """Return a dict shaped like one item of state.find_transitions()."""
    return {"id": site_id, "name": site_id, "old": old, "new": new, "reason": reason}


class FormatAlertTests(unittest.TestCase):
    """format_alert: one short line per change."""

    def test_change(self):
        line = notify.format_alert(transition("cafe", "UP", "BROKEN", "menu missing"))
        self.assertEqual(line, "[cafe] UP -> BROKEN: menu missing")

    def test_first_check_and_recovery(self):
        self.assertIn("NEW -> DOWN", notify.format_alert(transition("a", None, "DOWN", "timed out")))
        self.assertIn("back to normal", notify.format_alert(transition("a", "DOWN", "UP", "")))


class BuildMessageTests(unittest.TestCase):
    """build_message: one notification per run."""

    def test_title_counts_changes(self):
        title, body = notify.build_message([transition("a", "UP", "DOWN", "x"),
                                            transition("b", "UP", "BROKEN", "y")])
        self.assertEqual(title, "Site Watchdog: 2 changes")
        self.assertEqual(len(body.splitlines()), 2)

    def test_long_list_is_cut(self):
        many = [transition(f"s{i}", "UP", "DOWN", "x") for i in range(25)]
        title, body = notify.build_message(many)
        lines = body.splitlines()
        self.assertEqual(len(lines), notify.MAX_ALERT_LINES + 1)
        self.assertEqual(lines[-1], "... and 5 more")


class GetTopicTests(unittest.TestCase):
    """get_topic: the secret topic comes only from the environment."""

    def setUp(self):
        # Remember and remove any real topic, so the test controls the variable.
        self.old_value = os.environ.pop(notify.TOPIC_ENV_VAR, None)

    def tearDown(self):
        os.environ.pop(notify.TOPIC_ENV_VAR, None)
        if self.old_value is not None:
            os.environ[notify.TOPIC_ENV_VAR] = self.old_value

    def test_missing_topic(self):
        with self.assertRaises(ValueError):
            notify.get_topic()

    def test_bad_topics(self):
        for bad in ["bad topic!", "abc", "x/../y", "a" * 65]:
            os.environ[notify.TOPIC_ENV_VAR] = bad
            with self.assertRaises(ValueError):
                notify.get_topic()

    def test_good_topic(self):
        os.environ[notify.TOPIC_ENV_VAR] = "agency-alerts-42"
        self.assertEqual(notify.get_topic(), "agency-alerts-42")


if __name__ == "__main__":
    unittest.main()
