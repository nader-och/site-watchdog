"""Build alert messages and send them to the ntfy phone notification service.

The ntfy topic works like a password: anyone who knows it can read the
alerts. That is why it is read from the WATCHDOG_NTFY_TOPIC environment
variable and never stored in the config file or the repository.
"""

import os
import re

import requests

TOPIC_PATTERN = r"[A-Za-z0-9_-]{6,64}"
TOPIC_ENV_VAR = "WATCHDOG_NTFY_TOPIC"
NTFY_SERVER = "https://ntfy.sh"
MAX_ALERT_LINES = 20


def get_topic():
    """Return the ntfy topic from the environment, or raise ValueError.

    Called before any page is checked, so a missing or bad topic stops the
    run before a single network request is made.
    """
    topic = os.environ.get(TOPIC_ENV_VAR, "").strip()
    if not topic:
        raise ValueError(
            f"--notify needs the {TOPIC_ENV_VAR} environment variable "
            f"(PowerShell: $env:{TOPIC_ENV_VAR} = \"your-secret-topic\")"
        )
    if not re.fullmatch(TOPIC_PATTERN, topic):
        raise ValueError(
            f"{TOPIC_ENV_VAR} is not a valid topic name "
            "(use 6-64 letters, digits, '_' or '-')"
        )
    return topic


def format_alert(transition):
    """Return one short line for a status change, e.g.
    "[cafe-atlas] UP -> BROKEN: selector ".menu-item" matched nothing"."""
    old = transition["old"] or "NEW"
    reason = transition["reason"] or "back to normal"
    return f"[{transition['id']}] {old} -> {transition['new']}: {reason}"


def build_message(transitions):
    """Return (title, body) for one notification that lists all changes.

    One message per run (not one per site) avoids flooding the phone. The
    title stays plain ASCII because HTTP headers cannot carry Arabic text;
    site names and reasons go in the UTF-8 body instead.
    """
    count = len(transitions)
    title = f"Site Watchdog: {count} change{'s' if count != 1 else ''}"
    lines = []
    for transition in transitions[:MAX_ALERT_LINES]:
        lines.append(format_alert(transition))
    if count > MAX_ALERT_LINES:
        lines.append(f"... and {count - MAX_ALERT_LINES} more")
    return title, "\n".join(lines)


def send_ntfy(topic, title, message, timeout=10):
    """POST `message` to the ntfy topic. Return None on success, or a short
    error text on failure. It never raises, so a notification problem cannot
    crash the run or stop the state from being saved."""
    try:
        response = requests.post(
            f"{NTFY_SERVER}/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.HTTPError as error:
        return f"ntfy rejected the alert (HTTP {error.response.status_code})"
    except requests.RequestException as error:
        return f"could not reach ntfy ({type(error).__name__})"
    return None
