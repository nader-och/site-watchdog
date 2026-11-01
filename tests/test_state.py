"""Tests for watchdog/state.py: saved state and transition detection.
No network is used."""

import os
import tempfile
import unittest

from watchdog import state


def result(site_id, status, reason=""):
    """Return a dict shaped like one result of probe.check_site()."""
    return {"id": site_id, "name": site_id.title(), "status": status,
            "reason": reason, "elapsed_ms": 100}


def saved(status, since="2026-10-27T10:00:00+00:00"):
    """Return one saved state entry."""
    return {"name": "x", "status": status, "since": since}


class FindTransitionsTests(unittest.TestCase):
    """find_transitions: when do we alert?"""

    def test_same_status_no_alert(self):
        old = {"a": saved("DOWN")}
        self.assertEqual(state.find_transitions(old, [result("a", "DOWN")]), [])

    def test_change_is_alerted(self):
        old = {"a": saved("UP")}
        changes = state.find_transitions(old, [result("a", "BROKEN", "selector")])
        self.assertEqual(len(changes), 1)
        self.assertEqual((changes[0]["old"], changes[0]["new"]), ("UP", "BROKEN"))

    def test_recovery_is_alerted(self):
        old = {"a": saved("DOWN")}
        changes = state.find_transitions(old, [result("a", "UP")])
        self.assertEqual((changes[0]["old"], changes[0]["new"]), ("DOWN", "UP"))

    def test_first_check_is_baseline(self):
        # New and UP: silent. New and DOWN: alert, with old = None.
        self.assertEqual(state.find_transitions({}, [result("a", "UP")]), [])
        changes = state.find_transitions({}, [result("b", "DOWN")])
        self.assertIsNone(changes[0]["old"])


class UpdateStateTests(unittest.TestCase):
    """update_state: the "since" time and removed sites."""

    def test_since_kept_when_unchanged_and_reset_when_changed(self):
        old = {"a": saved("UP"), "b": saved("UP")}
        new = state.update_state(old, [result("a", "UP"), result("b", "DOWN")])
        self.assertEqual(new["a"]["since"], old["a"]["since"])
        self.assertNotEqual(new["b"]["since"], old["b"]["since"])

    def test_removed_sites_are_dropped(self):
        old = {"a": saved("UP"), "gone": saved("UP")}
        new = state.update_state(old, [result("a", "UP")])
        self.assertNotIn("gone", new)


class NowUtcTests(unittest.TestCase):
    """now_utc: the stored time format."""

    def test_is_utc_iso_text(self):
        self.assertTrue(state.now_utc().endswith("+00:00"))


class LoadSaveTests(unittest.TestCase):
    """load_state / save_state on real files in a temporary folder."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "state.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_missing_file_is_empty_state(self):
        self.assertEqual(state.load_state(self.path), {})

    def test_save_then_load_keeps_unicode(self):
        data = {"zeytin": {"name": "مطعم الزيتون", "status": "UP",
                           "since": state.now_utc()}}
        state.save_state(self.path, data)
        self.assertEqual(state.load_state(self.path), data)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_corrupt_file_raises_and_is_not_changed(self):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write('{"a": ')
        with self.assertRaises(ValueError):
            state.load_state(self.path)
        with open(self.path, encoding="utf-8") as file:
            self.assertEqual(file.read(), '{"a": ')

    def test_wrong_shape_raises(self):
        state.save_state(self.path, ["not", "a", "dict"])
        with self.assertRaises(ValueError):
            state.load_state(self.path)


if __name__ == "__main__":
    unittest.main()
