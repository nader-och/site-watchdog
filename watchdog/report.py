"""Format and print the status tables shown in the terminal.

Times are stored in UTC (one unambiguous clock for the program) and only
converted to Istanbul time here, at the moment they are shown to a person.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DISPLAY_ZONE = ZoneInfo("Europe/Istanbul")
TIME_FORMAT = "%d %b %H:%M"
# Problems first: the worst status gets the smallest number.
STATUS_ORDER = {"DOWN": 0, "HTTP_ERROR": 1, "BROKEN": 2, "SLOW": 3, "UP": 4}
NO_VALUE = "—"


def format_since(iso_text):
    """Turn stored UTC text like "2026-10-27T15:05:00+00:00" into "27 Oct 18:05"
    in Istanbul time. Anything that is not a valid time shows "unknown"."""
    try:
        moment = datetime.fromisoformat(iso_text)
    except (TypeError, ValueError):
        return "unknown"
    # A time without a zone would be read as local time; ours are always UTC.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(DISPLAY_ZONE).strftime(TIME_FORMAT)


def format_ms(elapsed_ms):
    """Return "118 ms", or a dash when there is no time (the site was DOWN)."""
    if elapsed_ms is None:
        return NO_VALUE
    return f"{elapsed_ms} ms"


def sort_key(status, site_id):
    """Sort key that puts problems first, then orders by id."""
    return (STATUS_ORDER.get(status, 0), site_id)


def id_width(ids):
    """Width of the id column: the longest id, but at least 4 ("ID" + space)."""
    return max([4] + [len(site_id) for site_id in ids])


def print_check_table(results):
    """Print one line per checked site: id, status, response time, reason."""
    ordered = sorted(results, key=lambda r: sort_key(r["status"], r["id"]))
    width = id_width([r["id"] for r in results])
    for result in ordered:
        time_text = format_ms(result["elapsed_ms"])
        line = f"  {result['id']:<{width}}  {result['status']:<10}  {time_text:>8}"
        if result["reason"]:
            line += f"   {result['reason']}"
        print(line)


def print_state_report(state):
    """Print the saved state: status, last response time and since when
    (in Istanbul time) for every site."""
    if not state:
        print("No saved state yet. Run 'python cli.py check' first.")
        return
    ids = sorted(state, key=lambda site_id: sort_key(state[site_id]["status"], site_id))
    width = id_width(ids)
    print(f"  {'ID':<{width}}  {'STATUS':<10}  {'TIME':>8}  {'SINCE (Istanbul)':<16}  NAME")
    for site_id in ids:
        entry = state[site_id]
        time_text = format_ms(entry.get("elapsed_ms"))
        since = format_since(entry["since"])
        name = entry.get("name", "")
        print(f"  {site_id:<{width}}  {entry['status']:<10}  {time_text:>8}  {since:<16}  {name}")
