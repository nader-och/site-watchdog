<!-- DRAFT: commit this only after running the tests and robustness rows in your handoff document. Delete any sentence that is not true for you, then delete this comment. -->

# Contributions: Muhammed Mustafa Adsan (2409011010, SyraxLL)

## My part
Part C: checking pages.

## Files I own and committed
- `watchdog/probe.py`
- `tests/test_probe.py`
- `contributions/MuhammedMustafaAdsan_2409011010_SyraxLL.md` (this file)

## What each function in my files does
- `fetch(url, timeout)`: makes the HTTP GET request with a timeout and a
  redirect limit, streams the body, measures the time with `perf_counter`,
  and returns status code, time, HTML and an error text instead of raising.
- `read_body(response, start, timeout)`: reads the body in chunks and stops at
  1 MB or when the total time passes the timeout.
- `describe_connection_error(error, timeout)`: turns a long connection error
  into a short reason (timeout, DNS, refused, could not connect).
- `has_expected_content(html, selector)`: parses the page with BeautifulSoup
  and returns True if the CSS selector matches at least one element.
- `classify(result, selector, slow_ms)`: returns exactly one status (UP, SLOW,
  BROKEN, HTTP_ERROR, DOWN) and a reason.
- `check_site(site, timeout, slow_ms)`: fetch + classify for one site.
- `check_all(sites, timeout, slow_ms)`: checks all sites and retries a DOWN
  site once after 1 second, at most 3 retries per run.
- `tests/test_probe.py`: 12 unit tests for the content check, every
  classification branch and the retry, without network.

## Design decisions in this part
- Network problems never raise out of the module; they become a DOWN result, so one bad site cannot stop the run.
- `stream=True` with a 1 MB limit, so a huge response is never fully downloaded.
- A total time limit while reading the body, because the requests timeout applies to each wait for data.
- The content check uses a CSS selector, so a page that answers 200 but lost its content is BROKEN, not UP.
- Statuses are checked from worst to best, so every site gets exactly one status.
- One retry with a budget, to avoid false alarms without making runs slow.

## Tests and robustness rows I ran
- `python -m unittest` on the finished project: 59 tests, OK.
- `python -m unittest tests.test_probe -v`: my 12 tests, all OK.
- Section 6 robustness rows 8–13 with the local test server and the commands
  from my handoff document; every row gave the expected status and reason.

## What I can explain
How a page is requested, timed and size-limited; which exceptions are caught
and why their order matters; how BeautifulSoup's `select` checks the content;
how `classify` picks one status; how the retry and its budget work; and what
each of my unit tests checks.
