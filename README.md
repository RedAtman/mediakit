# MediaKit

MediaKit is a CLI tool for batch media operations — compress, convert, scale, trim, and more. Uses ffmpeg via subprocess with in-process dynamic CPU throttling (SIGSTOP/SIGCONT), SQLAlchemy for state tracking, and a middleware-scheduler pattern for CLI dispatch.

## Installation

```sh
# Prerequisites

brew install ffmpeg
brew install RedAtman/tap/transcriber

# Create virtual environment and install dependencies
uv venv .venv && source .venv/bin/activate && uv sync

# (Optional) Install as a system-wide command
uv tool install --editable . --python 3.14
```

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

Use PID file at `~/.mediakit/daemon.pid` to track the running daemon. See `src/schedulers/folder.py:_stop()` and `src/schedulers/watcher.py` for implementation details.

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

`macOS/LaunchAgents/mediakit.plist` ships with the repo's venv entry point. Adjust if you use another install
(e.g. `/opt/homebrew/bin/mediakit`), and keep `WorkingDirectory` at the directory that owns `.env`, `db.db`
and `logs/`.

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

### Step 4: Stop / Unload

```sh
mediakit stop                                            # graceful; launchd leaves it down
launchctl bootout gui/$(id -u)/com.nut.mediakit          # remove the job entirely
launchctl kickstart -k gui/$(id -u)/com.nut.mediakit     # restart in place
```

### Notes

- **One instance only** — a second `mediakit compress --watch` exits with `watch daemon already running (PID …)`.
  The guard is in the app, so it works with or without launchd.
- **`KeepAlive` is `SuccessfulExit: false`** — a crash restarts the daemon, `mediakit stop` (SIGTERM, exit 0)
  keeps it down.
- **PATH** — launchd does not inherit your login shell's PATH, so the plist sets
  `EnvironmentVariables.PATH` (Homebrew first). Without it ffmpeg/ffprobe are not found and every task fails.
- **Logs** — launchd captures stdout/stderr into `logs/launchd.{out,err}`; the app's own rotating
  `logs/{info,warning,error}.log` stay the useful ones.

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

The file is automatically deleted after being read.

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
