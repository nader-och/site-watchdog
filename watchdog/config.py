"""Load and validate the sites config file (sites.json).

The config is a JSON list of client pages. Every entry is checked strictly
before any network request is made, so a typo or a dangerous URL is caught
early with a message that names the site index and the field.
"""

import ipaddress
import json
import os
import re
from urllib.parse import urlparse

# soupsieve is installed together with beautifulsoup4 and is the library that
# runs CSS selectors for it, so compiling with it checks the exact same syntax.
import soupsieve

MAX_CONFIG_BYTES = 100_000
MAX_SITES = 50
ID_PATTERN = r"[a-z0-9][a-z0-9-]{0,29}"
REQUIRED_KEYS = ("id", "name", "url", "expect")
MAX_NAME_LENGTH = 60
MAX_SELECTOR_LENGTH = 100
ALLOWED_SCHEMES = ("http", "https")


def load_sites(path, allow_local=False):
    """Read the config file at `path` and return a list of validated site dicts.

    Raises FileNotFoundError if the file is missing and ValueError for every
    other problem (folder, empty, too big, broken JSON, invalid entries).
    `allow_local` lets localhost and private addresses through (offline demo).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"sites file not found: {path}")
    if not os.path.isfile(path):
        raise ValueError(f"sites path is not a file: {path}")

    # Check the size before reading, so a huge file is never loaded into memory.
    size = os.path.getsize(path)
    if size == 0:
        raise ValueError(f"sites file is empty: {path}")
    if size > MAX_CONFIG_BYTES:
        raise ValueError(
            f"sites file is too large: {size} bytes (limit {MAX_CONFIG_BYTES})"
        )

    try:
        # utf-8-sig also accepts the invisible BOM that Windows Notepad adds.
        with open(path, encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"sites file is not valid JSON: {error.msg} "
            f"(line {error.lineno}, column {error.colno})"
        ) from error
    except UnicodeDecodeError as error:
        raise ValueError("sites file is not UTF-8 text") from error
    except RecursionError as error:
        # Thousands of nested brackets would otherwise crash the JSON parser.
        raise ValueError("sites file is nested too deeply") from error

    if not isinstance(data, list):
        raise ValueError(
            f"sites file must contain a JSON list, got {type(data).__name__}"
        )
    if len(data) == 0:
        raise ValueError("sites file contains no sites")
    if len(data) > MAX_SITES:
        raise ValueError(f"too many sites: {len(data)} (limit {MAX_SITES})")

    sites = []
    seen_ids = set()
    for index, entry in enumerate(data):
        site = validate_site(entry, index, allow_local)
        if site["id"] in seen_ids:
            raise ValueError(f"sites[{index}].id: duplicate id '{site['id']}'")
        seen_ids.add(site["id"])
        sites.append(site)
    return sites


def validate_site(entry, index, allow_local=False):
    """Check one config entry and return it as a clean dict.

    `index` is the position in the list; it is used in every error message so
    the user knows exactly which entry and which field to fix.
    """
    where = f"sites[{index}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{where}: must be an object, got {type(entry).__name__}")

    # Unknown keys are refused so a typo like "exepct" is not silently ignored.
    unknown = sorted(set(entry) - set(REQUIRED_KEYS))
    if unknown:
        raise ValueError(f"{where}: unknown field(s): {', '.join(unknown)}")
    for key in REQUIRED_KEYS:
        if key not in entry:
            raise ValueError(f"{where}.{key}: missing required field")
        if not isinstance(entry[key], str):
            raise ValueError(
                f"{where}.{key}: must be a string, got {type(entry[key]).__name__}"
            )

    site_id = entry["id"]
    if not re.fullmatch(ID_PATTERN, site_id):
        raise ValueError(
            f"{where}.id: '{site_id}' is invalid "
            "(use 1-30 lowercase letters, digits or '-', starting with a letter or digit)"
        )

    name = entry["name"].strip()
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        raise ValueError(f"{where}.name: must be 1-{MAX_NAME_LENGTH} characters")

    selector = entry["expect"].strip()
    if not 1 <= len(selector) <= MAX_SELECTOR_LENGTH:
        raise ValueError(
            f"{where}.expect: CSS selector must be 1-{MAX_SELECTOR_LENGTH} characters"
        )
    check_selector(selector, where, site_id)

    url = entry["url"].strip()
    check_url(url, where, allow_local)
    return {"id": site_id, "name": name, "url": url, "expect": selector}


def check_selector(selector, where, site_id):
    """Raise ValueError if `selector` is not valid CSS selector syntax.

    Checking it here means a typo such as "div[" is reported by validate,
    before any page is downloaded, instead of showing up later as BROKEN.
    """
    try:
        soupsieve.compile(selector)
    except soupsieve.SelectorSyntaxError as error:
        raise ValueError(
            f"{where}.expect: invalid CSS selector \"{selector}\" for site '{site_id}'"
        ) from error


def check_url(url, where, allow_local):
    """Raise ValueError if `url` is not a safe http/https address."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        shown = parsed.scheme or "none"
        raise ValueError(
            f"{where}.url: scheme must be http or https (got {shown}): {url}"
        )
    if not parsed.hostname:
        raise ValueError(f"{where}.url: missing host name: {url}")
    # Credentials in a URL end up in logs and alerts, so they are never allowed.
    if parsed.username or parsed.password:
        raise ValueError(f"{where}.url: must not contain a username or password")
    try:
        parsed.port  # reading .port raises ValueError for a port like 99999
    except ValueError as error:
        raise ValueError(f"{where}.url: invalid port: {url}") from error
    if not allow_local and is_local_host(parsed.hostname):
        raise ValueError(
            f"{where}.url: local/private address '{parsed.hostname}' is refused "
            "(use --allow-local for an offline demo)"
        )


def is_local_host(hostname):
    """Return True if `hostname` points at this machine or a private network.

    This stops the tool from being used to probe internal machines.
    Only literal names and IP addresses are checked (no DNS lookup).
    """
    name = hostname.lower().rstrip(".")
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        # Real domain names never end in a number. Forms like "127.1" or
        # "2130706433" are IP shorthands that can hide 127.0.0.1, so refuse them.
        last_label = name.rsplit(".", 1)[-1]
        return last_label.isdigit() or last_label.startswith("0x")
    return (
        address.is_loopback
        or address.is_private
        or address.is_unspecified
        or address.is_link_local
    )
