
# Contributions: Berivan Ertugrul (2409111006, Berivanertugrul)

## My part
Part D: memory and alerts.

## Files I own and committed
- `watchdog/state.py`
- `watchdog/notify.py`
- `tests/test_state.py`
- `tests/test_notify.py`
- `contributions/BerivanErtugrul_2409111006_Berivanertugrul.md` (this file)

## What each function in my files does
- `load_state(path)`: returns the saved state, `{}` if the file does not exist,
  and raises a clear error for a corrupt or wrong-shaped file without overwriting it.
- `check_state_shape(state, path)`: checks that the state is a dict of entries
  with a valid status and a `since` text.
- `save_state(path, state)`: writes the state to a `.tmp` file and swaps it in
  with `os.replace`, so the file is never half-written.
- `now_utc()`: returns the current UTC time as ISO 8601 text.
- `find_transitions(old_state, results)`: returns the sites whose status
  changed, plus new sites that are not UP.
- `update_state(old_state, results)`: builds the new state, keeps `since` when
  the status is unchanged and drops sites that left the config.
- `get_topic()`: reads the ntfy topic from `WATCHDOG_NTFY_TOPIC` and checks it
  with a regex before any request.
- `format_alert(transition)`: makes one short alert line.
- `build_message(transitions)`: makes one notification (title and body) for all changes.
- `send_ntfy(topic, title, message, timeout=10)`: sends the alert with an HTTP
  POST and returns an error text instead of raising.
- `tests/test_state.py` (11 tests) and `tests/test_notify.py` (7 tests): unit
  tests for the functions above; nothing is sent over the network.

## Design decisions in this part
- Alerts only on status changes, so the same problem does not send repeated alerts.
- A first check is a baseline: only a site that starts out not UP is reported.
- Atomic save with a temporary file and `os.replace`.
- A corrupt state file stops the run and is never overwritten.
- Times are stored in UTC.
- The ntfy topic is a secret, so it comes from an environment variable, not from the repo.
- Sending never raises, and the state is saved before alerts are sent.

## Tests and robustness rows I ran
- `python -m unittest` on the finished project: 59 tests, OK.
- `python -m unittest tests.test_state tests.test_notify -v`: my 18 tests, all OK.
- Section 6 robustness rows 15, 16, 17, 18 and 20 with the commands from my
  handoff document; every row gave the expected result.

## What I can explain
How the state is loaded, checked and saved atomically; how transitions are
found and why the first check is a baseline; why times are stored in UTC; how
the alert text is built and sent to ntfy with an HTTP POST; why the topic is
kept in an environment variable; and what each of my unit tests checks.
