"""Tests for watchdog/config.py: loading and validating sites.json."""

import json
import os
import tempfile
import unittest

from watchdog import config


def good_site(**changes):
    """Return a valid config entry, with some fields replaced by `changes`."""
    site = {"id": "pizza-roma", "name": "Pizza Roma",
            "url": "https://example.com/menu", "expect": ".menu-item"}
    site.update(changes)
    return site


class ValidateSiteTests(unittest.TestCase):
    """validate_site: one entry at a time."""

    def test_valid_site_is_returned_clean(self):
        site = config.validate_site(good_site(name="  Pizza Roma  "), 0)
        self.assertEqual(site["name"], "Pizza Roma")

    def test_bad_ids_are_rejected(self):
        for bad_id in ["../../x", "my site", "Pizza", "-start", "", "a" * 31]:
            with self.assertRaises(ValueError):
                config.validate_site(good_site(id=bad_id), 0)

    def test_error_names_index_and_field(self):
        with self.assertRaises(ValueError) as caught:
            config.validate_site(good_site(name=42), 3)
        self.assertIn("sites[3].name", str(caught.exception))

    def test_unknown_and_missing_keys(self):
        with self.assertRaises(ValueError):
            config.validate_site(good_site(exepct="typo"), 0)
        entry = good_site()
        del entry["expect"]
        with self.assertRaises(ValueError):
            config.validate_site(entry, 0)

    def test_bad_urls_are_rejected(self):
        bad_urls = ["file:///etc/passwd", "ftp://example.com", "javascript:alert(1)",
                    "example.com", "http://", "http://user:pass@site.com",
                    "http://example.com:99999/"]
        for url in bad_urls:
            with self.assertRaises(ValueError):
                config.validate_site(good_site(url=url), 0)

    def test_invalid_selector_is_rejected_with_site_name(self):
        with self.assertRaises(ValueError) as caught:
            config.validate_site(good_site(id="cafe-atlas", expect="div["), 2)
        message = str(caught.exception)
        self.assertIn("sites[2].expect", message)
        self.assertIn("cafe-atlas", message)
        # A valid but more complex selector is accepted.
        config.validate_site(good_site(expect="ul.menu > li:nth-child(2)"), 0)

    def test_local_urls_need_allow_local(self):
        for url in ["http://localhost/", "http://127.0.0.1/", "http://192.168.1.1/"]:
            with self.assertRaises(ValueError):
                config.validate_site(good_site(url=url), 0)
            config.validate_site(good_site(url=url), 0, allow_local=True)


class IsLocalHostTests(unittest.TestCase):
    """is_local_host: which host names count as local or private."""

    def test_local_names(self):
        for host in ["localhost", "127.0.0.1", "127.5.5.5", "0.0.0.0", "::1",
                     "10.0.0.8", "192.168.1.1", "2130706433"]:
            self.assertTrue(config.is_local_host(host), host)

    def test_public_names(self):
        for host in ["example.com", "8.8.8.8", "shop.example.org"]:
            self.assertFalse(config.is_local_host(host), host)


class LoadSitesTests(unittest.TestCase):
    """load_sites: whole files, using a temporary folder."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def write(self, text):
        """Write `text` to a temp sites file and return its path."""
        path = os.path.join(self.folder.name, "sites.json")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    def test_valid_file(self):
        path = self.write(json.dumps([good_site(), good_site(id="cafe")]))
        self.assertEqual(len(config.load_sites(path)), 2)

    def test_missing_folder_and_empty(self):
        with self.assertRaises(FileNotFoundError):
            config.load_sites(os.path.join(self.folder.name, "nope.json"))
        with self.assertRaises(ValueError):
            config.load_sites(self.folder.name)
        with self.assertRaises(ValueError):
            config.load_sites(self.write(""))

    def test_broken_json_and_not_a_list(self):
        with self.assertRaises(ValueError):
            config.load_sites(self.write("[{"))
        with self.assertRaises(ValueError):
            config.load_sites(self.write(json.dumps(good_site())))

    def test_duplicate_ids(self):
        path = self.write(json.dumps([good_site(), good_site()]))
        with self.assertRaises(ValueError):
            config.load_sites(path)

    def test_size_and_count_limits(self):
        with self.assertRaises(ValueError):
            config.load_sites(self.write(" " * (config.MAX_CONFIG_BYTES + 1)))
        sites = [good_site(id=f"s{i}") for i in range(config.MAX_SITES + 1)]
        with self.assertRaises(ValueError):
            config.load_sites(self.write(json.dumps(sites)))


if __name__ == "__main__":
    unittest.main()
