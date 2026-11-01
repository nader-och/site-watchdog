"""Remember the last status of every site (state.json) and detect changes.

The state file maps each site id to its last status and the UTC time that
status started. Comparing the saved state with a new check tells us which
sites changed, so we alert only on transitions (UP -> DOWN, DOWN -> UP...).
"""

import json
import os
from datetime import datetime, timezone

STATUSES = ("UP", "SLOW", "BROKEN", "HTTP_ERROR", "DOWN")


def load_state(path):
    """Return the saved state dict from `path`, or {} if the file does not exist.

    A corrupt or wrong-shaped file raises ValueError. The caller must stop
    then, so the file is never overwritten with empty data by mistake.
    """
    if not os.path.exists(path):
        return {}
    if not os.path.isfile(path):
        raise ValueError(f"state path is not a file: {path}")
    try:
        with open(path, encoding="utf-8") as file:
            state = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(
            f"state file {path} is corrupt ({error}); fix or delete it - "
            "it was NOT overwritten"
        ) from error
    check_state_shape(state, path)
    return state


def check_state_shape(state, path):
    """Raise ValueError unless `state` looks like {id: {"status", "since"}}."""
    if not isinstance(state, dict):
        raise ValueError(f"state file {path} must contain a JSON object")
    for site_id, entry in state.items():
        if not isinstance(entry, dict):
            raise ValueError(f"state file {path}: entry '{site_id}' is not an object")
        if entry.get("status") not in STATUSES:
            raise ValueError(f"state file {path}: entry '{site_id}' has a bad status")
        if not isinstance(entry.get("since"), str):
            raise ValueError(f"state file {path}: entry '{site_id}' has a bad 'since'")


def save_state(path, state):
    """Write `state` to `path` atomically.

    We write a temporary file first and then swap it in with os.replace.
    If the program crashes halfway, the old state.json is still complete.
    """
    temp_path = str(path) + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        # ensure_ascii=False keeps Arabic/Turkish names readable in the file.
        json.dump(state, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)


def now_utc():
    """Return the current time in UTC as ISO 8601 text, e.g. 2026-10-27T15:05:00+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find_transitions(old_state, results):
    """Return a list of status changes between the saved state and `results`.

    A site seen for the first time is a baseline: it only counts as a change
    if it is not UP (we want to hear about a site that starts out broken).
    """
    transitions = []
    for result in results:
        previous = old_state.get(result["id"])
        old_status = previous["status"] if previous else None
        if old_status == result["status"]:
            continue  # same as last time: no alert
        if old_status is None and result["status"] == "UP":
            continue  # first check and healthy: nothing to report
        transitions.append({
            "id": result["id"],
            "name": result["name"],
            "old": old_status,
            "new": result["status"],
            "reason": result["reason"],
        })
    return transitions


def update_state(old_state, results):
    """Build the new state from the latest `results`.

    "since" is kept when the status did not change and reset when it did.
    Sites that are no longer in the config are dropped, because the new
    state is built only from the current results.
    """
    checked_at = now_utc()
    new_state = {}
    for result in results:
        previous = old_state.get(result["id"])
        if previous and previous["status"] == result["status"]:
            since = previous["since"]
        else:
            since = checked_at
        new_state[result["id"]] = {
            "name": result["name"],
            "status": result["status"],
            "since": since,
            "reason": result["reason"],
            "elapsed_ms": result["elapsed_ms"],
            "last_checked": checked_at,
        }
    return new_state
