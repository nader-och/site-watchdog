# Contributions: Nader Ochen (2309116429, nader-och)

## My part
Part A: integration and presentation. I chose the project idea and the team
split, I own and committed the Part A files, I reviewed and tested the whole
project, and I present it.

## Files I own and committed
- `cli.py`
- `watchdog/report.py`
- `watchdog/__init__.py`
- `README.md`
- `examples/sites.example.json`, `examples/site/pizza-roma.html`,
  `examples/site/cafe-atlas.html`, `examples/site/shop-nour.html`
- `.gitignore`, `requirements.txt`
- `tests/__init__.py`, `tests/test_report.py`, `tests/test_cli.py`
- `contributions/NaderOchen_2309116429_nader-och.md` (this file)

I also created the GitHub repository and invited the other three members.

## What each function in my files does
- `positive_number(text)` / `positive_int(text)`: argparse types that accept
  only numbers greater than 0, so wrong values give an argparse error.
- `add_check_options(subparser)`: adds the options shared by `check` and `watch`.
- `build_parser()`: creates the parser with the subcommands `validate`,
  `check`, `report` and `watch`.
- `handle_validate`, `handle_check`, `handle_report`, `handle_watch`: one small
  handler per subcommand.
- `run_check(args)`: one full check: topic, config, old state, page checks,
  table, transitions, save, alerts.
- `show_alerts(transitions, topic)`: prints the alerts, and sends them with `--notify`.
- `main()`: runs the chosen command; expected errors become a short message
  and exit code 1.
- `format_since(iso_text)`: shows a stored UTC time in Istanbul time, or "unknown".
- `format_ms(elapsed_ms)`, `sort_key(status, site_id)`, `id_width(ids)`:
  helpers for the tables.
- `print_check_table(results)` / `print_state_report(state)`: print the aligned
  tables, problems first.
- `tests/test_report.py` (7 tests) and `tests/test_cli.py` (8 tests): unit
  tests for the time display, the tables, the argument types, the parser and
  the exit codes.

## Design decisions in this part
- argparse subcommands with one handler each, and positive-number checks as argparse types.
- Only `cli.py` and `report.py` print; the other modules return data or raise errors.
- Exit code 0 when the run works (even with DOWN sites), 1 for input problems, 2 for wrong arguments.
- The run order: ntfy topic and corrupt state are checked before any request, and the state is saved before alerts are sent.
- Times are stored in UTC and shown in Istanbul time.
- `watch` schedules runs from one start time, so it does not drift.
- An offline demo with three local pages that show UP, BROKEN and DOWN.

## Tests and robustness rows I ran
- `python -m unittest` on the finished project: 59 tests, OK.
- `python -m unittest tests.test_report tests.test_cli -v`: my 15 tests, all OK.
- All 20 Section 6 robustness rows, with the test script from my handoff
  folder; every row gave the expected result.
- The offline demo from the README (`validate`, `check` twice, `report`).

## What I can explain
How the command line is parsed and each subcommand is run; the order of a
`check` run and why; how errors become exit codes; how times are stored in
UTC and shown in Istanbul time; how the tables are formatted; how `watch`
avoids drift; and, as the presenter, how the whole project works from the
config file to the phone alert.
