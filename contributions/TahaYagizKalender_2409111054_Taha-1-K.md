<!-- DRAFT: commit this only after running the tests and robustness rows in your handoff document. Delete any sentence that is not true for you, then delete this comment. -->

# Contributions: Taha Yagiz Kalender (2409111054, Taha-1-K)

## My part
Part B: config and validation.

## Files I own and committed
- `watchdog/config.py`
- `tests/test_config.py`
- `contributions/TahaYagizKalender_2409111054_Taha-1-K.md` (this file)

## What each function in my files does
- `load_sites(path, allow_local=False)`: checks that the file exists, is a file,
  is not empty and is at most 100,000 bytes, then parses the JSON, checks that
  it is a list of at most 50 sites, validates every entry and refuses duplicate ids.
- `validate_site(entry, index, allow_local=False)`: checks one entry: a JSON
  object with exactly the keys `id`, `name`, `url`, `expect`, all strings; the
  id format; name and selector length; then the selector and the URL.
- `check_selector(selector, where, site_id)`: compiles the CSS selector with
  soupsieve and raises a clear error naming the site if the syntax is invalid.
- `check_url(url, where, allow_local)`: accepts only http/https URLs with a
  host, no username or password, a valid port, and no local or private address
  unless `--allow-local` is used.
- `is_local_host(hostname)`: returns True for localhost, loopback, private,
  unspecified and link-local addresses, and for numeric IP shorthands.
- `tests/test_config.py`: 14 unit tests for the rules above, using temporary
  files and no network.

## Design decisions in this part
- All checks happen before any network request, so bad or dangerous input never reaches the network code.
- The file size is checked before `json.load`, so a huge file is never read into memory.
- `re.fullmatch` is used for ids, so the whole id must match the pattern.
- Unknown keys are refused, so typos are reported instead of ignored.
- Every error message names the site index and field, e.g. `sites[1].name`.
- Errors are raised as `ValueError` (or `FileNotFoundError`), and only `cli.py` prints them.

## Tests and robustness rows I ran
- `python -m unittest` on the finished project: 59 tests, OK.
- `python -m unittest tests.test_config -v`: my 14 tests, all OK.
- Section 6 robustness rows 1–7 and 14 with the commands from my handoff
  document; every row gave the expected error message and exit code.

## What I can explain
How `sites.json` is loaded and validated, step by step; why the size is
checked before parsing; how `re.fullmatch`, `urlparse`, `ipaddress` and
soupsieve are used; why local addresses and credentials are refused; and
what each of my unit tests checks.
