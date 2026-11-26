# MediaKit

MediaKit is a CLI tool for batch media operations — compress, convert, scale, trim, and more. Uses ffmpeg via subprocess with in-process dynamic CPU throttling (SIGSTOP/SIGCONT), SQLAlchemy for state tracking, and a middleware-scheduler pattern for CLI dispatch.

## Installation

### Prerequisites

| Requirement | Notes |
| --- | --- |
| `ffmpeg` / `ffprobe` | **Not bundled** — must be on `PATH` (`brew install ffmpeg`, `apt install ffmpeg`). Under launchd/cron, `PATH` is minimal, so either export `FFMPEG_BIN_DIR=/opt/homebrew/bin` or set `PATH` (the shipped plist does the latter) |
| Python 3.14 | Only for the source/uv installs; `uv` can fetch it (`uv python install 3.14`). The range is pinned `<3.15` because pyobjc has no 3.15 wheel |
| `transcriber` CLI | Optional — only the transcription action needs it (`brew install RedAtman/tap/transcriber`) |
| macOS or Linux | CPU throttling is implemented there; on Windows the daemon runs unthrottled with one warning |

### Option 1 — Homebrew (macOS)

```sh
brew install RedAtman/tap/mediakit ffmpeg
mediakit -v
```

### Option 2 — Prebuilt binary (no Python needed)

Every release attaches `mediakit-<os>-<arch>` (`mediakit-macos-arm64`, `mediakit-macos-x86_64`,
`mediakit-linux-x86_64`, `mediakit-windows-x86_64.exe`) — download it from the release page, make it executable and
put it on `PATH`:

```sh
chmod +x mediakit-macos-arm64 && sudo mv mediakit-macos-arm64 /usr/local/bin/mediakit
```

### Option 3 — uv / from source

```sh
git clone https://github.com/RedAtman/mediakit && cd mediakit
uv sync                                          # creates .venv with Python 3.14
uv tool install --editable . --python 3.14       # optional: `mediakit` on PATH
```

## First Run

```sh
# 1. write a commented starter to ~/.config/mediakit/config.toml (never overwrites)
mediakit --init-config

# 2. tell it which folders to watch — either a plain list ...
printf '%s\n' "~/Downloads/rs" >> ~/.config/mediakit/folders.txt
#    ... referenced from the config:  [watch] folders_file = "~/.config/mediakit/folders.txt"
#    ... or explicit entries in the config:
#    [[watch.folders]]
#    path = "~/Downloads/rs"

# 3. smoke-test on one folder (one-shot, no daemon)
mediakit compress -t video -f ~/Movies/rs

# 4. run as a daemon (Ctrl-C to stop, or `mediakit stop` from another shell)
mediakit compress -t video --watch
```

Templates live in the repo: `config.toml.example`, `folders.txt.example`.

### Where state lives

| What | Source / uv install | Homebrew or prebuilt binary |
| --- | --- | --- |
| Config | `~/.config/mediakit/config.toml` (`$XDG_CONFIG_HOME`) | same |
| Database | `<repo>/db.db`, or `[database] path` | `~/Library/Application Support/mediakit/db.db` (macOS), `~/.local/state/mediakit/db.db` (Linux), `%LOCALAPPDATA%\mediakit\db.db` (Windows) |
| Logs | `<repo>/logs/` | same platform state dir, `logs/` |
| Daemon pid | `~/.mediakit/daemon.pid` | same |

The frozen binary keeps **state next to the platform state dir, not next to the binary**, so `brew upgrade` cannot
lose your database; an `.env` (cwd or `~`) that sets `SQLITE_DATABASE` still overrides it.

## Usage

```sh
mediakit compress -t video -f /path/to/video/directory
```

### Watch Mode

Add `--watch` to any action command to monitor a folder for new/modified media files and process them automatically:

```sh
mediakit compress --watch -f /path/to/folder -t video -w 2
mediakit trim --watch -f /path/to/folder -t video
mediakit scale --watch -f /path/to/folder -t video
```

| Flag                 | Description                                                    | Default                         |
| -------------------- | -------------------------------------------------------------- | ------------------------------- |
| `--watch`            | Enable watch mode (add to any action)                          | `False`                         |
| `-f`                 | Folder to watch                                                | `MEDIA_FILE_FOLDER`             |
| `-t`                 | Media type (video/audio/image)                                 | `video`                         |
| `-w`                 | Number of worker threads                                       | `MAX_WORKERS`                   |
| `-c`                 | CPU limit per worker (%)                                       | auto                            |
| `--config`           | TOML config (default `~/.config/mediakit/config.toml`)         | `$XDG_CONFIG_HOME/mediakit/config.toml` |
| `--init-config`      | Write the starter config and exit (never overwrites)            | `False`                         |
| `--folder-file`      | Legacy plain-text folder list (one per line, # comments)       | —                               |
| `--recursive`        | Watch subdirectories                                           | `False` (non-recursive default) |
| `--no-scan-existing` | Skip processing existing files at startup                      | `False`                         |

#### Config file

Watch mode reads `~/.config/mediakit/config.toml` (override with `--config` or `MEDIAKIT_CONFIG`). Precedence:
`--config` → `MEDIAKIT_CONFIG` → `~/.config/mediakit/config.toml` → `~/.config/mediakit/folders.txt` → `-f DIR`.

```toml
[watch]
cpu_limit   = 200                          # global; `-c` wins
folders_file = "~/.config/mediakit/folders.txt"   # a plain one-path-per-line list still works

[compress]                                 # global defaults; `--resolution`/`--fps` win
fps = 24

[database]                                 # where db.db lives; an SQLITE_DATABASE env var wins
path = "~/Library/Application Support/mediakit/db.db"

[[watch.folders]]                          # per-directory overrides (longest prefix wins)
path       = "~/Downloads/rs/jp.gv"
media_type = "video"                       # video | audio | image
recursive  = true                          # this subtree only
compress   = { resolution = "HD", fps = 30 }
```

Start from a commented template instead of writing it by hand:

```sh
mediakit --init-config              # writes ~/.config/mediakit/config.toml (never overwrites)
mediakit --init-config --config /path/to/config.toml
```

The repo also ships `config.toml.example` and `folders.txt.example`; a test keeps the former byte-identical to
the text `--init-config` writes, so the example cannot drift from the schema.

`[database] path` is applied before any scheduler runs, so `db.db` can live outside the project (the frozen
binary already keeps it in the platform state dir). Note the precedence: an `SQLITE_DATABASE` in the environment
or in `.env` wins over this line — remove it there if you want the config file to decide, otherwise startup logs
a warning naming both values. `mediakit dedupe` follows the same database unless `--db` overrides it.

An invalid config aborts startup with a one-line message instead of being ignored, and so does a run with no
folders at all (`nothing to watch: no media folders configured` plus the three ways to fix it). Editing the file
while the daemon runs re-reads folders and `resolution`/`fps`; changing `recursive` needs a restart.

When no config file exists, the watcher falls back to `--folder-file`, then `~/.config/mediakit/folders.txt`
(a plain one-path-per-line list), then `-f DIR`.

### Stop the Watcher

Stop a running watch daemon gracefully, or force-stop immediately:

```sh
# Graceful stop (waits for in-flight media processing to finish)
mediakit stop

# Force stop (immediately kills daemon and all child ffmpeg processes)
mediakit stop --force
```

| Flag      | Description                                        | Default |
| --------- | -------------------------------------------------- | ------- |
| `--force` | Immediately kill all mediakit and ffmpeg processes | `False` |

The daemon writes `~/.mediakit/daemon.pid` **before** it starts compressing the startup backlog, so `mediakit stop`
and the single-instance guard work from the first second of a run — not after the backlog finishes. During that
drain a stop request takes effect at the next folder boundary. `MEDIAKIT_PID_DIR` moves the file (containers,
tests).

### Deduplicate Media Files

Find media files that share the same md5 (same content under different names) and move the duplicates to the macOS Trash (recoverable, not permanently deleted):

```sh
# Dry-run: list what would be removed (default)
mediakit dedupe

# Actually move duplicates to Trash
mediakit dedupe --apply
```

| Flag      | Description                                                           | Default |
| --------- | --------------------------------------------------------------------- | ------- |
| `--apply` | Move duplicate files to Trash instead of dry-run                      | `False` |
| `--db`    | Path to the media database (prefers the DB-recorded path as survivor) | `db.db` |

### Available Commands

| Command                 | Description                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| `compress`              | Compress media files (H.264/H.265, quality/size control)         |
| `scale`                 | Resize/rescale video resolution                                  |
| `trim`                  | Trim/cut video segments                                          |
| `change_file_extension` | Batch rename file extensions                                     |
| `convert_format`        | Convert between container formats                                |
| `save_text`             | Extract subtitle/text tracks                                     |
| `dedupe`                | Find media files with identical md5 and move duplicates to Trash |
| `stop`                  | Stop the running watch daemon (graceful or force)                |

## macOS LaunchAgent (Background Daemon)

MediaKit can run the watch daemon under launchd so it survives logout and restarts on crash. There is no
shell wrapper: launchd execs the entry point directly and the daemon owns everything else.

### Step 1: Configure Watch

Write `~/.config/mediakit/config.toml` (see [Config file](#config-file)) and confirm it loads:

```sh
mediakit compress -t video --watch --no-scan-existing   # Ctrl-C after it prints "Watching N folders"
```

### Step 2: Point the plist at Your Install

`macOS/LaunchAgents/mediakit.plist` ships with the Homebrew entry point (`/opt/homebrew/bin/mediakit`, the
Apple Silicon prefix — Intel Homebrew installs into `/usr/local/bin`). Running from a source checkout instead?
Point it at `<repo>/.venv/bin/mediakit`. Either way keep `WorkingDirectory` at the directory that owns `.env`,
`db.db` and `logs/`.

### Step 3: Install

```sh
# 1. strip Finder/cloud attributes: launchd refuses a quarantined plist with a bare
#    "Bootstrap failed: 5: Input/output error" while plutil -lint still reports OK
xattr -c macOS/LaunchAgents/mediakit.plist
cp macOS/LaunchAgents/mediakit.plist ~/Library/LaunchAgents/
xattr -c ~/Library/LaunchAgents/mediakit.plist

# 2. load it (starts now and on every login)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mediakit.plist

# 3. verify
launchctl print gui/$(id -u)/com.nut.mediakit | grep -E 'state|pid'
tail -3 logs/launchd.err
```

### Step 4: Start / Stop / Unload

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mediakit.plist   # only when not loaded yet
launchctl kickstart -k gui/$(id -u)/com.nut.mediakit                     # start or restart a loaded job
mediakit stop                                                           # graceful; launchd leaves it down
launchctl bootout gui/$(id -u)/com.nut.mediakit                          # unload the job entirely
```

`mediakit stop` leaves the job **loaded but not running** (that is how `KeepAlive { SuccessfulExit: false }` is
supposed to behave). Starting it again therefore needs `kickstart`; `bootstrap` on an already-loaded job fails with
`Bootstrap failed: 5: Input/output error`, which is a launchd quirk, not a plist problem.

### Notes

- **One instance only** — a second `mediakit compress --watch` exits with `watch daemon already running (PID …)`.
  The guard is in the app, so it works with or without launchd.
- **`KeepAlive` is `SuccessfulExit: false`** — a crash restarts the daemon, `mediakit stop` (SIGTERM, exit 0)
  keeps it down.
- **PATH** — launchd does not inherit your login shell's PATH, so the plist sets
  `EnvironmentVariables.PATH` (Homebrew first). Without it ffmpeg/ffprobe are not found and every task fails.
- **Logs** — launchd captures stdout/stderr into `logs/launchd.{out,err}`; the app's own rotating
  `logs/{info,warning,error}.log` stay the useful ones.

## Building

```sh
# lint + tests (what CI runs)
pre-commit run --all-files
uv run pytest -q

# sdist + wheel → dist/
uv build

# single-file binary (PyInstaller spec is the single source of truth for packaging)
uv run --with pyinstaller==6.22.3 pyinstaller mediakit.spec --distpath dist --workpath build
```

Notes on the frozen build:

- `mediakit.spec` carries the pieces static analysis cannot see: `utils/media_types.json`, the distribution metadata
  (`mediakit -v` reads it), and the dynamically imported logger/signal modules. Adding a new dynamic import means
  adding it there, or the binary fails at runtime.
- `ffmpeg` is **not** bundled — the binary shells out to a system ffmpeg on `PATH`, exactly like the pip/uv install.
- `multiprocessing` is excluded on purpose: PyInstaller's runtime hook spawns a helper that re-enters the frozen CLI
  and breaks argument parsing. Nothing here uses processes (`utils/executor.py` is thread-only).

## Releasing

```sh
# 1. bump the only version source
$EDITOR pyproject.toml          # [project].version
uv lock                         # syncs mediakit's version in the lock

# 2. commit, then tag the exact commit and push the tag
git commit -am "chore(release): x.y.z"
git tag vX.Y.Z && git push origin vX.Y.Z
```

`.github/workflows/release.yml` then: runs pre-commit + the test suite (a tag can point at anything, so the release
is gated on tests), refuses to publish unless the tag equals `[project].version`, builds sdist+wheel, builds the
binary for macOS arm64/x86_64, Linux x86_64 and Windows, attaches all of them to the GitHub release, and dispatches
a Homebrew formula bump. Tags containing `alpha`, `beta` or `rc` are published as prereleases. The tagged commit must
be reachable from `main` — the workflow checks that too.

## Dynamic CPU Throttling

MediaKit has a built-in dynamic CPU throttler using `SIGSTOP`/`SIGCONT` signals. It monitors each ffmpeg process's CPU usage in real-time and dynamically adjusts.

The throttler has three layers:

- **`CPULimiterCoordinator`** — Scheduler layer: manages throttler instances for all worker processes, handles manual overrides, SIGUSR1 signals, and file-based overrides
- **`ProcessThrottler`** — One daemon thread per monitored process: samples CPU usage and calculates SIGSTOP/SIGCONT durations via duty cycle controller
- **`macos_sample_cpu_time()`** — Sampling layer: macOS prefers `ps` subprocess (avoids `proc_pidinfo` ctypes struct incompatibility on macOS 26), falls back to `proc_pidinfo` or Linux `/proc/stat`

### Method 1: Auto Mode (Default)

Configure via the `CPU_LIMIT` environment variable (default `CPU_LIMIT=100`, i.e., 100%). This is used directly as the total budget distributed to all workers:

| Env Variable              | Per-Worker Budget              |
| ------------------------- | ------------------------------ |
| `CPU_LIMIT=100` (default) | 100% / worker count            |
| `CPU_LIMIT=50`            | 50% / worker count             |
| `CPU_LIMIT=1`             | 1% / worker count (minimum 1%) |

### Method 2: CLI Argument

```sh
# -c/--cpu-limit: Set CPU limit (100 = single core, i.e., 100%)
mediakit compress -t video -f /path/to/dir -c 50   # Limit to 50%
```

### Method 3: Runtime Signal (SIGUSR1)

Cycle through preset profiles at runtime (unlimited → 100% → 50% → 25%):

```sh
# Find the process PID
ps aux | grep python

# Each SIGUSR1 advances to the next profile
kill -SIGUSR1 <pid>   # → 100%
kill -SIGUSR1 <pid>   # → 50%
kill -SIGUSR1 <pid>   # → 25%
kill -SIGUSR1 <pid>   # → unlimited (auto mode)
```

**Design note**: SIGUSR1 is a Unix signal and cannot carry a numeric parameter. The solution is a fixed cycle — each SIGUSR1 advances to the next preset profile. For exact values, use Method 4 (file override).

**Note**: Send the signal to the main `mediakit` process (not to ffmpeg subprocesses). The signal handler is registered via `signal.signal()` and executes reliably even when the main thread is blocked in `subprocess.communicate()` (Python uses a self-pipe trick internally).

### Method 4: File Override

Create a special file to set a temporary CPU limit:

```sh
# Format: /tmp/mediakit_cpu_<percentage>
touch /tmp/mediakit_cpu_25   # Set 25% limit
```

The file is automatically deleted after being read, and the change is logged at **WARNING** so it always shows up
in `mediakit`'s own logs (they are rotated in `logs/warning.log`; a daemon started with `LOG_LEVEL=WARNING` writes
nothing at INFO level, which used to make a successful override look like a no-op):

```
CPU budget override: 25% total (~25%/worker) from mediakit_cpu_25
```

The new budget applies to the *next* throttle decision; if no ffmpeg process is running yet, only the budget changes.

### Multi-Worker Behavior

When using `-w/--workers` for parallel processing, the CPU quota is divided equally among all workers, with a floor of 1% (manual mode via `-c`) or 25% (auto mode).

Example: `-c 100 -w 4` gives each worker 25% in manual mode; auto mode `CPU_LIMIT=50 -w 4` gives each worker 12% (clamped to the 25% auto-mode safety floor).

### Configuration Priority

1. File override (highest priority)
2. CLI `--cpu-limit` argument (manual mode)
3. Environment variable `CPU_LIMIT` (auto mode default budget)
4. Auto mode default (uses CPU_LIMIT directly)

### Duty Cycle Control

When ffmpeg's CPU usage exceeds the target, the throttler calculates a proportional stop duration:

```
stop_time = window_duration × (actual_CPU / target - 1)
```

Example: a process at 500% targeting 25% gives `stop_time = 1.0 × (500/25 - 1) = 19s`. The process runs for ~1s then stops for ~19s, achieving an effective ~25% CPU.

This is more precise than fixed-duration stops and adapts to processes with different CPU intensities. Stop duration is bounded between 0.5s (minimum) and 30s (maximum). When the target changes while the process is stopped, the throttler recalculates and may wake the process immediately.

### macOS Compatibility

macOS 26 (Sequoia) has a `proc_pidinfo()` ctypes struct layout mismatch with the kernel output, causing ~42x sampling error. The throttler uses `ps` subprocess as the primary sampling method, with `proc_pidinfo` as fallback for systems without `ps`.
