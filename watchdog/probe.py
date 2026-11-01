"""Check one web page: HTTP request, timing, size limit, content check, status.

A page is only "UP" if the server answers with 200, quickly, AND the page
still contains the content we expect (found with a CSS selector). Network
problems never raise out of this module: they become a DOWN result.
"""

import time

import requests
from bs4 import BeautifulSoup
# soupsieve is installed together with beautifulsoup4; it does the CSS
# selector work and raises this error for a selector like "div[".
from soupsieve import SelectorSyntaxError

MAX_BYTES = 1_000_000
MAX_REDIRECTS = 5
CHUNK_SIZE = 64 * 1024
HEADERS = {"User-Agent": "SiteWatchdog/1.0 (student project)"}
RETRY_WAIT_SECONDS = 1
RETRY_BUDGET = 3


def fetch(url, timeout):
    """Download `url` and return {"status_code", "elapsed_ms", "html", "error"}.

    On success "error" is None. On any network failure "error" holds a short
    human-readable reason and "status_code" / "elapsed_ms" are None.
    """
    result = {"status_code": None, "elapsed_ms": None, "html": "", "error": None}
    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS
    start = time.perf_counter()
    try:
        # stream=True means the body is not downloaded yet, so we can stop
        # reading as soon as it gets too big.
        response = session.get(url, timeout=timeout, stream=True, headers=HEADERS)
        with response:
            body, error = read_body(response, start, timeout)
        if error:
            result["error"] = error
            return result
        result["status_code"] = response.status_code
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000)
        # Selectors only use tag and class names (plain ASCII), so decoding
        # as UTF-8 and replacing odd bytes is always safe for the check.
        result["html"] = body.decode("utf-8", errors="replace")
    # Timeout must come first: a connect timeout is also a ConnectionError.
    except requests.Timeout:
        result["error"] = f"timed out after {timeout:g} s"
    except requests.TooManyRedirects:
        result["error"] = f"too many redirects (more than {MAX_REDIRECTS})"
    except requests.ConnectionError as error:
        result["error"] = describe_connection_error(error, timeout)
    except requests.RequestException as error:
        result["error"] = f"request failed ({type(error).__name__})"
    finally:
        session.close()
    return result


def read_body(response, start, timeout):
    """Read the response body in chunks and return (bytes, error_or_None).

    Stops early if the body passes MAX_BYTES, or if the whole download takes
    longer than `timeout` (a server could send one byte per second forever).
    """
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        total += len(chunk)
        if total > MAX_BYTES:
            return b"", f"response too large (over {MAX_BYTES:,} bytes)"
        if time.perf_counter() - start > timeout:
            return b"", f"timed out after {timeout:g} s"
        chunks.append(chunk)
    return b"".join(chunks), None


def describe_connection_error(error, timeout):
    """Turn a long requests.ConnectionError into a short reason for the table."""
    text = str(error)
    # A read timeout while streaming the body arrives as a ConnectionError.
    if "timed out" in text:
        return f"timed out after {timeout:g} s"
    if "NameResolution" in text or "getaddrinfo" in text:
        return "host name not found (DNS lookup failed)"
    if "refused" in text:
        return "connection refused (nothing listening on that port)"
    return "could not connect to the server"


def has_expected_content(html, selector):
    """Return True if the CSS `selector` matches at least one element in `html`.

    An invalid selector is a mistake in sites.json, not in the page, so it is
    raised as ValueError with a clear message instead of crashing. config.py
    already refuses invalid selectors; this is a second safety net for code
    that calls the probe directly.
    """
    try:
        matches = BeautifulSoup(html, "html.parser").select(selector)
    except SelectorSyntaxError as error:
        raise ValueError(f'invalid CSS selector "{selector}"') from error
    return len(matches) > 0


def classify(result, selector, slow_ms):
    """Turn a fetch result into exactly one (status, reason) pair.

    Checks run from "worst" to "best", so the first failing check decides.
    """
    if result["error"]:
        return "DOWN", result["error"]
    code = result["status_code"]
    if code >= 400:
        return "HTTP_ERROR", f"HTTP {code}"
    if code != 200:
        return "BROKEN", f"unexpected HTTP {code} (expected 200)"
    if not result["html"].strip():
        return "BROKEN", "page is empty"
    try:
        found = has_expected_content(result["html"], selector)
    except ValueError as error:
        return "BROKEN", f"config error: {error}"
    if not found:
        return "BROKEN", f'selector "{selector}" matched nothing'
    if result["elapsed_ms"] > slow_ms:
        return "SLOW", f"took {result['elapsed_ms']} ms (limit {slow_ms} ms)"
    return "UP", ""


def check_site(site, timeout, slow_ms):
    """Run one full check of `site` and return a result dict. Never raises
    for network problems: those become a DOWN result."""
    fetched = fetch(site["url"], timeout)
    status, reason = classify(fetched, site["expect"], slow_ms)
    return {
        "id": site["id"],
        "name": site["name"],
        "status": status,
        "reason": reason,
        "elapsed_ms": fetched["elapsed_ms"],
    }


def check_all(sites, timeout, slow_ms):
    """Check every site in order and return the list of result dicts.

    A DOWN site gets one more attempt after a short wait, because a single
    network hiccup should not cause a false alarm. RETRY_BUDGET limits the
    retries per run, so a run with many dead sites still finishes quickly.
    """
    results = []
    retries_left = RETRY_BUDGET
    for site in sites:
        result = check_site(site, timeout, slow_ms)
        if result["status"] == "DOWN" and retries_left > 0:
            retries_left -= 1
            time.sleep(RETRY_WAIT_SECONDS)
            result = check_site(site, timeout, slow_ms)
            if result["status"] == "DOWN":
                result["reason"] += " (retried once)"
        results.append(result)
    return results
