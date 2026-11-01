"""Site Watchdog command-line interface.

Checks a list of client web pages, remembers the last result in state.json
and alerts (preview by default, ntfy with --notify) only when a status
changes. Run "python cli.py --help" for the commands.
"""

import argparse
import math
import sys
import time

from watchdog import config, notify, probe, report, state


def positive_number(text):
    """argparse type: accept a number greater than 0 (e.g. --timeout 2.5)."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a number")
    # isfinite also refuses "nan" and "inf", which float() accepts.
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be greater than 0, got {text}")
    return value


def positive_int(text):
    """argparse type: accept a whole number greater than 0 (e.g. --runs 3)."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a whole number")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be greater than 0, got {text}")
    return value


def add_check_options(subparser):
    """Add the options shared by "check" and "watch"."""
    subparser.add_argument("--sites", required=True, help="sites config file (JSON)")
    subparser.add_argument("--state", default="state.json", help="state file (default: state.json)")
    subparser.add_argument("--timeout", type=positive_number, default=5,
                           help="seconds to wait for each page (default: 5)")
    subparser.add_argument("--slow-ms", type=positive_int, default=2000,
                           help="slower than this many ms = SLOW (default: 2000)")
    subparser.add_argument("--notify", action="store_true",
                           help="send alerts to ntfy (default: preview only)")
    subparser.add_argument("--allow-local", action="store_true",
                           help="allow localhost/private addresses (offline demo)")


def build_parser():
    """Create the argparse parser with one subcommand per action."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Site Watchdog: check client pages and alert only when a status changes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="check the sites file without any network request")
    validate.add_argument("--sites", required=True, help="sites config file (JSON)")
    validate.add_argument("--allow-local", action="store_true",
                          help="allow localhost/private addresses (offline demo)")
    validate.set_defaults(handler=handle_validate)

    check = subparsers.add_parser("check", help="check every site once and show alerts")
    add_check_options(check)
    check.set_defaults(handler=handle_check)

    report_parser = subparsers.add_parser("report", help="show the saved status of every site")
    report_parser.add_argument("--state", default="state.json", help="state file (default: state.json)")
    report_parser.set_defaults(handler=handle_report)

    watch = subparsers.add_parser("watch", help="repeat check every N seconds for a fixed number of runs")
    add_check_options(watch)
    watch.add_argument("--every", type=positive_number, required=True, help="seconds between runs")
    watch.add_argument("--runs", type=positive_int, required=True, help="number of runs")
    watch.set_defaults(handler=handle_watch)
    return parser


def handle_validate(args):
    """Validate the sites file and list the sites it contains."""
    sites = config.load_sites(args.sites, allow_local=args.allow_local)
    print(f"OK: {len(sites)} site(s) in {args.sites}")
    width = max(len(site["id"]) for site in sites)
    for site in sites:
        print(f"  {site['id']:<{width}}  {site['url']}  expect \"{site['expect']}\"")


def handle_check(args):
    """Check every site once (see run_check)."""
    run_check(args)


def handle_report(args):
    """Print the saved state as a table, with times in Istanbul time."""
    report.print_state_report(state.load_state(args.state))


def handle_watch(args):
    """Run check args.runs times, args.every seconds apart.

    Run number n is scheduled at start + n * every. Sleeping only until that
    planned time (instead of sleeping "every" seconds after each run) means
    slow checks do not push the schedule later and later (no drift).
    """
    start = time.monotonic()
    for run in range(args.runs):
        planned = start + run * args.every
        wait = planned - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        offset = time.monotonic() - start
        print(f"--- run {run + 1}/{args.runs} at {time.strftime('%H:%M:%S')} (+{offset:.1f} s) ---")
        run_check(args)


def run_check(args):
    """One full check: load config and state, check pages, compare, save, alert."""
    # Fail early: a missing ntfy topic or a corrupt state file must stop the
    # run before any page is requested and before anything is overwritten.
    topic = notify.get_topic() if args.notify else None
    sites = config.load_sites(args.sites, allow_local=args.allow_local)
    old_state = state.load_state(args.state)

    started = time.perf_counter()
    results = probe.check_all(sites, args.timeout, args.slow_ms)
    print(f"Checked {len(results)} site(s) in {time.perf_counter() - started:.2f} s")
    report.print_check_table(results)

    transitions = state.find_transitions(old_state, results)
    # Save before sending: a notification problem must never lose the state.
    state.save_state(args.state, state.update_state(old_state, results))
    show_alerts(transitions, topic)


def show_alerts(transitions, topic):
    """Print the alerts, and send them to ntfy if a topic was given."""
    if not transitions:
        print("No changes since last check - no alerts.")
        return
    if topic is None:
        print("Alerts (preview - add --notify to send):")
    else:
        print("Alerts:")
    for transition in transitions:
        print(f"  {notify.format_alert(transition)}")
    if topic is None:
        return
    title, message = notify.build_message(transitions)
    error = notify.send_ntfy(topic, title, message)
    if error:
        print(f"warning: alert not sent: {error} (state was saved)", file=sys.stderr)
    else:
        print(f"Sent {len(transitions)} alert(s) to ntfy.")


def main():
    """Parse the command line, run the chosen command, and turn expected
    errors into a short message and exit status 1 instead of a traceback."""
    # Windows uses an old code page when output is redirected to a file;
    # UTF-8 keeps Arabic/Turkish site names from crashing the program.
    # line_buffering keeps normal output and warnings in the right order.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("stopped by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
