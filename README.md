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

| Flag | Description | Default |
|------|-------------|---------|
| `--watch` | Enable watch mode (add to any action) | `False` |
| `-f` | Folder to watch | `MEDIA_FILE_FOLDER` |
| `-t` | Media type (video/audio/image) | `video` |
| `-w` | Number of worker threads | `MAX_WORKERS` |
| `-c` | CPU limit per worker (%) | auto |
| `--folder-file` | Path to text file with folder paths (one per line, # comments) | — |
| `--recursive` | Watch subdirectories | `False` (non-recursive default) |
| `--no-scan-existing` | Skip processing existing files at startup | `False` |

When `--folder-file` is not specified and `-f` is not explicitly set, the watcher reads from the default file (`var/folder.sh`) and falls back to `MEDIA_FILE_FOLDER`.

### Stop the Watcher

Stop a running watch daemon gracefully, or force-stop immediately:

```sh
# Graceful stop (waits for in-flight media processing to finish)
mediakit stop

# Force stop (immediately kills daemon and all child ffmpeg processes)
mediakit stop --force
```

| Flag | Description | Default |
|------|-------------|---------|
| `--force` | Immediately kill all mediakit and ffmpeg processes | `False` |

Use PID file at `~/.mediakit/daemon.pid` to track the running daemon. See `src/schedulers/folder.py:_stop()` and `src/schedulers/watcher.py` for implementation details.

### Available Commands

| Command | Description |
|---------|-------------|
| `compress` | Compress media files (H.264/H.265, quality/size control) |
| `scale` | Resize/rescale video resolution |
| `trim` | Trim/cut video segments |
| `change_file_extension` | Batch rename file extensions |
| `convert_format` | Convert between container formats |
| `save_text` | Extract subtitle/text tracks |
| `stop` | Stop the running watch daemon (graceful or force) |

## macOS LaunchAgent (Scheduled Service)

MediaKit can run as a scheduled service via macOS LaunchAgent — useful for unattended batch processing (e.g., watching a folder).

### Step 1: Configure Virtual Environment
Ensure dependencies are installed and `.venv` is set up (see Installation above).

### Step 2: Edit `watcher.sh`
`watcher.sh` automatically activates the virtual environment and delegates to `watcher_.sh` for the main processing loop. Edit the `ENV` variable in `watcher_.sh` to switch between `development`/`production` if needed.

### Step 3: Configure LaunchAgent
An example plist is provided at `macOS/LaunchAgents/mediakit.plist`.

Key fields:
- `ProgramArguments`: Absolute path to `watcher.sh`
- `StartInterval`: Execution interval in seconds (e.g., 60 = every minute)
- `WorkingDirectory`: Must point to the project root
- `StandardOutPath` / `StandardErrorPath`: Log output paths

### Step 4: Install / Uninstall the Service

```sh
# Install (auto-start on boot + scheduled)
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/mediakit.plist

# Uninstall
launchctl bootout gui/$(id -u) macOS/LaunchAgents/mediakit.plist
```

### Step 5: View Logs

Log files are written to the `logs/` directory (e.g., `logs/watcher.log.YYYY-MM-DD.log`).

### Notes
- `watcher.sh` automatically activates the `.venv` environment and calls `watcher_.sh`
- `watcher_.sh` checks if the script is already running to prevent duplicate processes
- Debugging: run `watcher.sh` manually or via crontab

## Dynamic CPU Throttling

MediaKit has a built-in dynamic CPU throttler using `SIGSTOP`/`SIGCONT` signals. It monitors each ffmpeg process's CPU usage in real-time and dynamically adjusts.

The throttler has three layers:
- **`CPULimiterCoordinator`** — Scheduler layer: manages throttler instances for all worker processes, handles manual overrides, SIGUSR1 signals, and file-based overrides
- **`ProcessThrottler`** — One daemon thread per monitored process: samples CPU usage and calculates SIGSTOP/SIGCONT durations via duty cycle controller
- **`macos_sample_cpu_time()`** — Sampling layer: macOS prefers `ps` subprocess (avoids `proc_pidinfo` ctypes struct incompatibility on macOS 26), falls back to `proc_pidinfo` or Linux `/proc/stat`

### Method 1: Auto Mode (Default)

Configure via the `CPU_LIMIT` environment variable (default `CPU_LIMIT=100`, i.e., 100%). This is used directly as the total budget distributed to all workers:

| Env Variable | Per-Worker Budget |
|-------------|-------------------|
| `CPU_LIMIT=100` (default) | 100% / worker count |
| `CPU_LIMIT=50` | 50% / worker count |
| `CPU_LIMIT=1` | 1% / worker count (minimum 1%) |

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
