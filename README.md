# Site Watchdog

A smoke detector for small client websites: it checks each page, remembers the
last result, and sends a phone alert **only when something changes**.

## 1. Problem

A small web agency hosts menu and landing pages for local restaurants and shops.
When a page breaks, the owner usually notices before the agency does. A server
can answer "200 OK" while the page is empty because a plugin failed, so simply
asking "is the server online?" is not enough.

Site Watchdog checks that every page:

- answers in time,
- answers with HTTP 200,
- **still shows real content** (a CSS selector such as `.menu-item` must match).

It stores the last status of every site and alerts only on transitions
(UP → DOWN, DOWN → UP, UP → BROKEN, ...), so nobody gets the same alert every
few minutes.

## 2. Installation (Windows PowerShell)

Python 3.10 or newer is required. From the folder that contains `site-watchdog`:

```powershell
cd site-watchdog
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` holds `requests`, `beautifulsoup4` and `tzdata` (Windows has
no built-in time-zone database, and `zoneinfo` needs it for Istanbul time).

**Troubleshooting**

- If `.venv\Scripts\activate` says the file or module is not found, your
  `python` command is probably not the python.org Python (for example an MSYS2
  or Git-Bash Python, which puts the scripts in `.venv\bin`). Use the Python
  launcher instead:

  ```powershell
  Remove-Item -Recurse -Force .venv
  py -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  ```

- If PowerShell says running scripts is disabled, allow local scripts for your
  user account once, then try `activate` again:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 3. Usage

Command summary (`FILE`, `SEC`, `MS` and `N` are placeholders, not literal text):

```text
python cli.py validate --sites FILE [--allow-local]
python cli.py check    --sites FILE [--state FILE] [--timeout SEC] [--slow-ms MS] [--notify] [--allow-local]
python cli.py report   [--state FILE]
python cli.py watch    --sites FILE --every SEC --runs N [same options as check]
python cli.py --help
```

Defaults: `--state state.json`, `--timeout 5`, `--slow-ms 2000`.
The exit status is 0 when the run worked, even if some sites are down (a down
site is a result, not a crash). It is 1 for a problem such as a bad config
file, and 2 for a wrong command-line argument.

### Offline demo

The `examples` folder has three tiny pages and a config that points at them.
Open a **second** PowerShell window and start a local web server there:

```powershell
cd site-watchdog
.venv\Scripts\activate
python -m http.server 8000 --bind 127.0.0.1 --directory examples\site
```

Nothing listens on port 8001 yet, so `shop-nour` is DOWN on purpose. Run the
commands below in the **first** window (venv active, inside `site-watchdog`).
Your times in ms will differ from the ones shown.

**validate** checks the config without any network request. `--allow-local`
is needed because the demo uses `127.0.0.1`:

```
PS> python cli.py validate --sites examples\sites.example.json --allow-local
OK: 3 site(s) in examples\sites.example.json
  pizza-roma  http://127.0.0.1:8000/pizza-roma.html  expect ".menu-item"
  cafe-atlas  http://127.0.0.1:8000/cafe-atlas.html  expect ".menu-item"
  shop-nour   http://127.0.0.1:8001/shop-nour.html  expect ".product"

PS> python cli.py validate --sites examples\sites.example.json
error: sites[0].url: local/private address '127.0.0.1' is refused (use --allow-local for an offline demo)
```

**check**, first run. Alerts are only previewed. A site seen for the first time
is a baseline, so only sites that are not UP are reported (`NEW -> ...`):

```
PS> python cli.py check --sites examples\sites.example.json --allow-local
Checked 3 site(s) in 5.19 s
  shop-nour   DOWN               —   connection refused (nothing listening on that port) (retried once)
  cafe-atlas  BROKEN         10 ms   selector ".menu-item" matched nothing
  pizza-roma  UP             87 ms
Alerts (preview - add --notify to send):
  [cafe-atlas] NEW -> BROKEN: selector ".menu-item" matched nothing
  [shop-nour] NEW -> DOWN: connection refused (nothing listening on that port) (retried once)
```

The run takes about 5 s because the DOWN site is retried once after 1 s, and
on Windows a refused local connection takes about 2 s each time.

**check** again. Nothing changed, so there is no repeated alert:

```
PS> python cli.py check --sites examples\sites.example.json --allow-local
Checked 3 site(s) in 5.13 s
  shop-nour   DOWN               —   connection refused (nothing listening on that port) (retried once)
  cafe-atlas  BROKEN         14 ms   selector ".menu-item" matched nothing
  pizza-roma  UP             20 ms
No changes since last check - no alerts.
```

**report** shows the saved state. Times are stored in UTC and shown in
Istanbul time:

```
PS> python cli.py report
  ID          STATUS          TIME  SINCE (Istanbul)  NAME
  shop-nour   DOWN               —  27 Oct 21:23      Shop Nour
  cafe-atlas  BROKEN         14 ms  27 Oct 21:23      Café Atlas
  pizza-roma  UP             20 ms  27 Oct 21:23      Pizza Roma
```

**Recovery.** Open a **third** window and start a server on port 8001 as well:

```powershell
cd site-watchdog
.venv\Scripts\activate
python -m http.server 8001 --bind 127.0.0.1 --directory examples\site
```

Back in the first window:

```
PS> python cli.py check --sites examples\sites.example.json --allow-local
Checked 3 site(s) in 0.13 s
  cafe-atlas  BROKEN         24 ms   selector ".menu-item" matched nothing
  pizza-roma  UP              6 ms
  shop-nour   UP             97 ms
Alerts (preview - add --notify to send):
  [shop-nour] DOWN -> UP: back to normal
```

**watch** repeats `check`. Each run is planned from the start time
(+0, +10, +20 s), so the schedule does not drift:

```
PS> python cli.py watch --sites examples\sites.example.json --allow-local --every 10 --runs 3
--- run 1/3 at 21:24:16 (+0.0 s) ---
Checked 3 site(s) in 0.08 s
  cafe-atlas  BROKEN         18 ms   selector ".menu-item" matched nothing
  pizza-roma  UP             29 ms
  shop-nour   UP             27 ms
No changes since last check - no alerts.
--- run 2/3 at 21:24:26 (+10.0 s) ---
...
--- run 3/3 at 21:24:36 (+20.0 s) ---
...
```

Stop the servers with Ctrl+C in their windows.

### Phone alerts with ntfy

1. Install the free **ntfy** app on your phone and subscribe to a hard-to-guess
   topic, e.g. `agency-watchdog-7f3k9q`.
2. Put the topic in an environment variable (never in the config or the repo)
   and add `--notify`:

```powershell
$env:WATCHDOG_NTFY_TOPIC = "agency-watchdog-7f3k9q"
python cli.py check --sites examples\sites.example.json --allow-local --notify
```

When a status has changed since the last run, this prints the alert lines and
then `Sent N alert(s) to ntfy.` (one notification lists all N changes). If ntfy
cannot be reached, it prints a warning, and the state is still saved. Without
`--notify`, nothing is sent and the alerts are only printed (preview).

### Tests

```powershell
python -m unittest
```

59 unit tests, one test file per module (see the structure below). They use
no network: the CLI tests only run `validate` and argument errors.

## 4. Config file format (`sites.json`)

A JSON **list** of objects with exactly these four string fields:

```json
[
  {
    "id": "pizza-roma",
    "name": "Pizza Roma",
    "url": "https://example.com/menu.html",
    "expect": ".menu-item"
  }
]
```

| Field | Rule |
|---|---|
| `id` | 1–30 characters: lowercase letters, digits, `-`; starts with a letter or digit; unique |
| `name` | 1–60 characters, any language (UTF-8) |
| `url` | `http://` or `https://`, must have a host, no `user:password@`, no local/private address unless `--allow-local` |
| `expect` | a valid CSS selector (1–100 characters) that must match something on a healthy page |

Limits: at most 50 sites and 100,000 bytes per file. Unknown fields are
refused, so a typo such as `"exepct"` is reported instead of ignored. Every
error names the site index and the field, e.g.
`sites[1].name: must be a string, got int` or
`sites[0].expect: invalid CSS selector "div[" for site 'bad-selector'`.

## 5. Status meanings

| Status | Meaning |
|---|---|
| `UP` | HTTP 200, faster than `--slow-ms`, expected content found |
| `SLOW` | like UP, but slower than `--slow-ms` |
| `BROKEN` | HTTP 200 (or another non-error code) but the page is empty or the selector matched nothing |
| `HTTP_ERROR` | the server answered 4xx or 5xx |
| `DOWN` | timeout, connection refused, DNS failure, too many redirects, or response over 1 MB |

A `DOWN` result is retried once after 1 second (at most 3 retries per run), so
a single network hiccup does not cause a false alarm.

## 6. Project structure

```
site-watchdog/
├── cli.py
├── watchdog/
│   ├── __init__.py
│   ├── config.py
│   ├── probe.py
│   ├── state.py
│   ├── notify.py
│   └── report.py
├── examples/
│   ├── sites.example.json
│   └── site/
│       ├── pizza-roma.html
│       ├── cafe-atlas.html
│       └── shop-nour.html
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_probe.py
│   ├── test_state.py
│   ├── test_notify.py
│   ├── test_report.py
│   └── test_cli.py
├── contributions/
├── requirements.txt
├── README.md
└── .gitignore
```

| Path | What it is |
|---|---|
| `cli.py` | The program you run. Reads the command line with `argparse` (subcommands `validate`, `check`, `report`, `watch`), calls the modules in the right order, and turns errors into short messages and exit codes. |
| `watchdog/` | The package with the program's logic, one module per job. |
| `watchdog/__init__.py` | Marks `watchdog` as a Python package, so `from watchdog import config` works. |
| `watchdog/config.py` | Loads `sites.json` and validates it strictly: size and count limits, JSON errors, id regex, URL rules, CSS selector syntax, local-address block. |
| `watchdog/probe.py` | Checks one page: HTTP request with timeout, redirect and size limits, timing, CSS selector content check, classification into one status, and the single retry for DOWN sites. |
| `watchdog/state.py` | Loads and saves `state.json` safely (atomic write), and finds the transitions between the saved and the new statuses. |
| `watchdog/notify.py` | Reads the secret ntfy topic from the environment, builds the alert text and sends it to ntfy with an HTTP POST. |
| `watchdog/report.py` | Prints the aligned status tables and converts stored UTC times to Istanbul time. |
| `examples/` | Everything needed for the offline demo. |
| `examples/sites.example.json` | Demo config with three sites on `127.0.0.1` (needs `--allow-local`). |
| `examples/site/` | The folder served by `python -m http.server` in the demo. |
| `examples/site/pizza-roma.html` | Healthy menu page: has `.menu-item` elements, so it is UP. |
| `examples/site/cafe-atlas.html` | Menu page whose list is empty, so it is BROKEN. |
| `examples/site/shop-nour.html` | Product page, expected on port 8001: DOWN until a server runs on that port. |
| `tests/` | Unit tests (`unittest`), one file per module. Run with `python -m unittest`. |
| `tests/__init__.py` | Marks `tests` as a package, so `python -m unittest` finds the test files. |
| `tests/test_config.py` | Tests config validation: ids, URLs, local addresses, selectors, limits, broken files. |
| `tests/test_probe.py` | Tests the content check, every classification branch, and the retry and its budget (with a fake `check_site`, no network). |
| `tests/test_state.py` | Tests transitions, `since` handling, removed sites, saving and loading, and the corrupt-file case. |
| `tests/test_notify.py` | Tests alert lines, the combined message, and the topic checks (nothing is sent). |
| `tests/test_report.py` | Tests Istanbul time display, the `unknown` fallback, and the table order and content. |
| `tests/test_cli.py` | Tests the number argument types, the parser defaults, and exit codes 0, 1 and 2. |
| `contributions/` | One Markdown file per team member describing their part. |
| `requirements.txt` | The three libraries to install with pip. |
| `README.md` | This file. |
| `.gitignore` | Keeps runtime and local files out of git: `state.json`, `*.tmp`, `__pycache__/`, `*.pyc`, `.venv/`, `.env`, `.DS_Store`. |

Created when you use the tool, never committed: `.venv/` (the virtual
environment) and `state.json` (the saved statuses, created by `check`).

## 7. Safety design

- **Strict validation** before any request: regex for ids (`re.fullmatch`),
  `urllib.parse` for URLs, CSS selectors compiled with `soupsieve`, size and
  count limits, no unknown fields.
- **Only http/https**: `file:///etc/passwd`, `ftp://` and `javascript:` are refused.
- **No credentials in URLs**: they would leak into logs and alerts.
- **Local-address block**: `localhost`, `127.x`, `0.0.0.0`, `::1`, private
  ranges (checked with `ipaddress`) and numeric shorthands such as `2130706433`
  are refused unless `--allow-local` is given, so the tool cannot be pointed at
  internal machines.
- **Timeouts** on every request, plus a total download deadline.
- **Size limit**: the body is streamed and reading stops after 1 MB.
- **Redirect limit**: at most 5 redirects.
- **Atomic state**: `state.json` is written to `state.json.tmp` first and then
  swapped in with `os.replace`, so a crash never leaves a half-written file.
  A corrupt state file stops the run and is **not** overwritten.
- **Preview by default**: alerts are only sent with `--notify`.
- **Secret topic**: the ntfy topic comes from `WATCHDOG_NTFY_TOPIC`, never from
  the config or the repository. A failed notification is reported and the
  state is still saved.

## 8. Limitations

- Checks one page per site.
- No JavaScript rendering: content added by JavaScript after loading is not seen.
- The content check depends on a CSS selector; a redesign can rename the class
  and make a healthy page look BROKEN until the config is updated.
- The local-address block checks the URL text only. A public domain name whose
  DNS points at a private address, or a public page that redirects to one, is
  not detected.
- Sites are checked one after another, so many slow sites make a run longer.
