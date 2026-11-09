# mediakit

[![CI](https://github.com/RedAtman/mediakit/actions/workflows/ci.yml/badge.svg)](https://github.com/RedAtman/mediakit/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/RedAtman/mediakit)](https://github.com/RedAtman/mediakit/releases)

A CLI for batch media operations on a folder tree: compress, scale, convert, reverse, combine, concatenate, extract text, rewrite metadata, and deduplicate. ffmpeg is driven over subprocess; every job is tracked in SQLite so an interrupted batch can resume; a `--watch` mode turns any action into a long-running daemon that processes files as they land.

The CPU cost of ffmpeg is controlled in-process: mediakit `SIGSTOP`/`SIGCONT`s the child processes it started and keeps them inside a CPU budget you set per core.

- **State, not fire-and-forget** — each media file gets a row with a per-action state; failures are recorded as `failed (-2)`, not lost
- **Resumable batches** — re-running an action skips what already finished
- **Watch mode** — debounce + file-stability tracking, so a file is compressed once it stops being written, not mid-copy
- **CPU budget** — one core per worker by default, adjustable at runtime with `SIGUSR1` or a marker file
- **Windows / macOS / Linux binaries** — no Python needed for the released builds

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Options](#options)
- [Watch mode](#watch-mode)
- [Stopping the daemon](#stopping-the-daemon)
- [Deduplication](#deduplication)
- [State, database and logs](#state-database-and-logs)
- [CPU throttling](#cpu-throttling)
- [Metadata and transcription](#metadata-and-transcription)
- [Configuration](#configuration)
- [macOS LaunchAgent](#macos-launchagent)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Requirements

| | |
| --- | --- |
| **ffmpeg + ffprobe** | required, **not bundled**. Must be on `PATH` or in `FFMPEG_BIN_DIR` |
| **transcriber** | only for `save_text` — `brew install RedAtman/tap/transcriber` |
| **Python 3.14** | only when installing from source (`>=3.14,<3.15`, pinned because pyobjc has no 3.15 wheels) |

## Installation

### Homebrew (recommended on macOS)

```sh
brew install RedAtman/tap/mediakit
brew install ffmpeg
```

The formula installs a self-contained binary; `brew upgrade mediakit` picks up new releases.

### Prebuilt binary

Every release ships `mediakit-<os>-<arch>` for macOS arm64/x86_64, Linux x86_64 and Windows x86_64:

```sh
curl -L -o mediakit https://github.com/RedAtman/mediakit/releases/latest/download/mediakit-macos-arm64
chmod +x mediakit && ./mediakit -v
```

### From source

```sh
git clone https://github.com/RedAtman/mediakit.git
cd mediakit
uv venv --python 3.14 && source .venv/bin/activate
uv sync
uv tool install --editable . --python 3.14    # exposes `mediakit` on PATH
```

## Quick start

```sh
# Compress every video in a folder, one at a time, at 50% of one core
mediakit compress -t video -f ~/Movies/inbox -w 1 -c 50

# Same, as a daemon: process new files as they arrive
mediakit compress -t video --watch -f ~/Movies/inbox

# Half a core per worker, downscaled to 1920x1080 at 30 fps
mediakit compress -t video -f ~/Movies/inbox --resolution FHD --fps 30 -c 50
```

## Commands

```
mediakit <action> [options]
```

| Action | What it does | Needs |
| --- | --- | --- |
| `compress` | x265 (libx265) re-encode at `crf=22`, optional downscale and fps | `-f` |
| `scale` | Rescale video to the target resolution (default 1920×1080) | `-f` |
| `convert_format` | Re-wrap/re-encode into another container | `-f` |
| `change_file_extension` | Rename extensions in bulk (no re-encode) | `-f --old_ext --ext` |
| `combine` | Logo overlay + background track with fade in/out + crop, one pass | `-f`, see note below |
| `reverse` | Reverse the video stream | `-f` |
| `decode` | Decode to a plain container (`mp4` by default) | `-f` |
| `delete_voice` | Strip the audio track | `-f` |
| `save_metadata` | Dump ffmetadata to `<title>_metadata.txt` | `-f` |
| `set_metadata` | Write title/keywords/artist metadata back into the file | `-f` |
| `images_to_video` | Build a video from an image sequence | `--images-path` |
| `concat` | Join clips through the concat demuxer | `--concat-list` |
| `save_text` | Transcribe audio to text via the external `transcriber` CLI | `-f`, `transcriber` on PATH |
| `dedupe` | Move byte-identical copies to the Trash (macOS) | see [Deduplication](#deduplication) |
| `stop` | Stop the running watch daemon | see [Stopping the daemon](#stopping-the-daemon) |

`combine` ships a hard-coded default watermark path (a developer machine path); if that file is missing ffmpeg fails, so treat it as “configure a logo before use” rather than zero-config.

Notes on scope: `change_file_extension` works on the folder itself, `images_to_video` on `--images-path` (its output is written next to the images), and `concat` on the list file, writing `concat_output.mov` next to that list — they ignore `-f`. The remaining actions process the media they find under `-f`.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `-f, --folder` | `MEDIA_FILE_FOLDER` (`samples`) | Folder to operate on |
| `-t, --type` | `all` | `video` / `audio` / `image`. **Honoured by `save_text` and `--watch`**; other actions are video-only today |
| `-w, --max_workers` | `MAX_WORKERS` (`1`) | Parallel jobs. Capped at `os.cpu_count()` |
| `-c, --cpu-limit` | `CPU_LIMIT` (`100`) | CPU budget **per worker**, 100 = one core. See [CPU throttling](#cpu-throttling) |
| `--resolution` | `COMPRESS_RESOLUTION` (`HD`) | `compress` output height/width: enum name (`HD`, `FHD`, `WQHD`, `UHD`, …) or `1920x1080`, case-insensitive. **Downscales only** — never enlarges |
| `--fps` | `COMPRESS_FPS` (`24`) | `compress` output frame rate, `>= 1` |
| `--watch` | off | Run the action as a daemon (see [Watch mode](#watch-mode)) |
| `--folder-file` | resolved `var/folder.sh` | Path to a folder list file |
| `--recursive` | off | Watch subdirectories |
| `--no-scan-existing` | off | Skip the startup scan; only handle files that arrive later |
| `--old_ext`, `--ext` | — | `change_file_extension` source/target extension |
| `--force` | off | `stop`: SIGKILL the process group instead of SIGTERM |
| `--apply` | off | `dedupe`: actually move duplicates instead of a dry run |
| `--db` | `db.db` | `dedupe`: database used to decide which copy survives |
| `--concat-list` | — | `concat`: path to a concat demuxer list file (`file '...'` lines) |
| `--images-path`, `--image-format`, `--bit-rate` | —, `jpg`, `5000k` | `images_to_video` inputs |
| `-v, --version` | — | Print the version (read from package metadata) |
| `-d, --daemon` | `True` | Accepted for compatibility; currently unused |

## Watch mode

`--watch` turns an action into a foreground daemon that reacts to filesystem events:

```sh
mediakit compress -t video --watch -f ~/Movies/inbox
mediakit compress -t video --watch --folder-file var/folder.sh -w 2 -c 50
mediakit compress -t video --watch --recursive --no-scan-existing --folder-file var/folder.sh
```

Folder list resolution, in order:

1. `--folder-file <path>` if given
2. `WATCH_FOLDER_FILE` from the environment
3. `var/folder.sh` found by walking up from the current directory
4. `var/folder.sh` found by walking up from the tool's own location (covers launchd, where the cwd is `/`)
5. otherwise `-f` / `MEDIA_FILE_FOLDER` as a single folder

The file is one folder per line; blank lines and `#` comments are ignored, paths are `~`-expanded, normalised and de-duplicated before anything is scheduled.

### What "watched" means

Each configured folder is an independent watch: its own filesystem stream, its own entry in the config-reload diff, its own startup scan. Editing the list while the daemon runs adds and removes exactly the lines that changed, without a restart, and newly added folders are scanned for pre-existing files.

`--recursive` watches subdirectories too; nested entries in the list are then collapsed into their parent, because a parent covers its children. Without `--recursive` a parent does **not** cover its children, so nested entries stay separate — do not replace a long list with a couple of ancestor roots: that would make one removed line stop watching a hundred folders, and would start processing directories nobody configured.

### Timing (observable behaviour, not tuning knobs)

| Stage | Value |
| --- | --- |
| Debounce calm period | 5 s after the last write |
| Debounce max flush | 60 s even if writes never stop |
| Stability check | size + mtime unchanged for 3 samples × 1 s |
| Stability give-up | 30 s |
| Config file poll | 5 s |

A file is processed once it has been quiet for 5 s and stable for 3 s — so a copy in progress is not compressed half-finished, and a stuck upload is abandoned after 30 s.

Cost, measured on 224 configured folders: 227 threads, ~2100 file descriptors, ~8 MB, and ~23 s before every stream is scheduled (~95 ms each; macOS serialises stream creation, so this cannot be parallelised). It is the price of per-folder identity, not an inefficiency.

### Logs and pid file

The daemon writes `~/.mediakit/daemon.pid` on start, removes it on a graceful exit, and logs to the `logs/` directory (see [State, database and logs](#state-database-and-logs)).

## Stopping the daemon

```sh
mediakit stop           # SIGTERM: finish in-flight jobs, then exit
mediakit stop --force   # SIGKILL the whole process group, ffmpeg children included
```

With nothing running it prints `No running daemon found.` and exits 0.

## Deduplication

Two files with the same md5 are the same content under different names. `dedupe` scans the watched folders, keeps one copy (preferring the path recorded in the database so the media table stays consistent) and moves the rest to the Trash via Finder — recoverable, not deleted. **macOS only**: it shells out to `osascript`, so elsewhere the move step does nothing.

```sh
mediakit dedupe                                   # dry run: what would move
mediakit dedupe --apply                           # move duplicates to the Trash
mediakit dedupe --apply --folder-file my-list.txt  # default: resolved var/folder.sh
mediakit dedupe --apply --db /path/to/db.db        # survivor preference comes from here
```

The dry run is the default on purpose: everything it prints is about to disappear from its folder.

## State, database and logs

Every action records per-media state in SQLite, so re-running an action resumes instead of redoing work:

| Value | Meaning |
| --- | --- |
| `2` | finished |
| `-1` | unprocessed / not applicable for this action |
| `-2` | failed — the next run retries it |
| `0` … `1` | in-flight progress fraction, written by `compress` while encoding |

Where the database and logs live:

| Install type | Location |
| --- | --- |
| From source | next to `config.py` (`db.db`, `logs/`) |
| Homebrew / binary (macOS) | `~/Library/Application Support/mediakit/` |
| Homebrew / binary (Windows) | `%LOCALAPPDATA%\mediakit\` |
| Homebrew / binary (Linux) | `~/.local/state/mediakit/` |

Binaries never write next to themselves: `brew upgrade` replaces the Cellar version directory, which would take the database and logs with it. Point `SQLITE_DATABASE` at a path to override this.

Logs are split by level — `default.log`, `info.log`, `warning.log`, `error.log`, `critical.log` — with `LOG_BACKUP_COUNT` rotated copies. `LOG_LEVEL` accepts any casing (`info`, `INFO`, `20`); an unknown value falls back to `WARNING` instead of aborting.

## CPU throttling

mediakit starts ffmpeg itself, so it can throttle it in-process: sample the child's CPU, then `SIGSTOP`/`SIGCONT` it on a duty cycle. No `nice`, no `cpulimit`, and it works with many workers at once.

Three layers:

- **`CPULimiterCoordinator`** — owns one throttler per worker process, splits the budget, handles manual overrides, `SIGUSR1` and file overrides (`utils/throttle/coordinator.py`)
- **`ProcessThrottler`** — one daemon thread per monitored process: samples CPU and computes the stop/run duty cycle (`utils/throttle/throttler.py`)
- **`macos_sample_cpu_time()`** — sampling: `ps` subprocess on macOS (avoids a `proc_pidinfo` ctypes struct mismatch that gives ~42× errors on macOS 26), `/proc/stat` on Linux (`utils/throttle/sampling.py`)

On any other platform the coordinator logs one warning and runs unthrottled rather than failing.

### Method 1 — environment default

`CPU_LIMIT` (default `100`) is the **total** budget, split evenly across workers:

| `CPU_LIMIT` | Per-worker budget with `-w 4` |
| --- | --- |
| `100` (default) | 25% each |
| `50` | 12% each |
| `1` | 1% each (floor) |

### Method 2 — CLI

```sh
mediakit compress -t video -f ~/Movies/inbox -c 50     # 50% per worker
mediakit compress -t video -f ~/Movies/inbox -w 4 -c 100   # 25% each
```

### Method 3 — runtime signal

```sh
kill -SIGUSR1 <pid>   # cycles: unlimited (auto) -> 100% -> 50% -> 25% -> unlimited
```

A Unix signal cannot carry a value, so the profiles are a fixed cycle. Send it to the mediakit process, not to ffmpeg: the handler is registered with `signal.signal()` and runs even while the main thread is blocked in `subprocess.communicate()`.

### Method 4 — marker file (exact value)

```sh
touch /tmp/mediakit_cpu_25   # 25% until the file is consumed and deleted
```

### Priority

marker file → `-c/--cpu-limit` → `CPU_LIMIT` → built-in default.

### Duty cycle

When a process exceeds its target, the stop duration is proportional rather than fixed:

```
stop_time = window_duration × (actual_cpu / target - 1)
```

A process at 500% targeting 25% stops for `1.0 × (500/25 - 1) = 19 s` after ~1 s of running, which averages to ~25%. Stops are bounded to 0.5–30 s, and a target change while stopped wakes the process immediately. The only floor in the code is 1% per worker (`MIN_PER_WORKER`), applied in both modes.

## Metadata and transcription

`set_metadata` writes title, keywords and artist into the file. Keywords are translated through the Baidu Translate API and enriched from the `CAMERA`, `LENS`, `CATEGORY` and `ARTIST` mappings in `config.py`; without Baidu credentials the translation step raises when it is reached, so `set_metadata` needs:

```sh
BAIDU_TRANSLATE_APP_ID=...
BAIDU_TRANSLATE_SECRET_KEY=...
BAIDU_TRANSLATE_SALT=...
```

`save_text` shells out to the external `transcriber` CLI (whisper.cpp based):

```sh
brew install RedAtman/tap/transcriber
mediakit save_text -t video -f ~/Movies/inbox
```

Transcription is configured with `TRANSCRIBER_MODEL` (default `base`) and `TRANSCRIBER_INITIAL_PROMPT`. The output lands next to the source as `<title>.txt`.

## Configuration

All settings are environment variables (a `.env` in the working directory is loaded, falling back to `~/.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `MEDIA_FILE_FOLDER` | `samples` | Default `-f` |
| `MAX_WORKERS` | `1` | Default `-w` |
| `CPU_LIMIT` | `100` | Total CPU budget (see [CPU throttling](#cpu-throttling)) |
| `COMPRESS_RESOLUTION` | `HD` | Default `--resolution` (1280×720) |
| `COMPRESS_FPS` | `24` | Default `--fps` |
| `SQLITE_DATABASE` | `db.db` | Database path (relative to the state directory) |
| `MEDIA_FILE_PATH` | `samples/zh.mp4` | Sample used by ad-hoc scripts |
| `WATCH_FOLDER_FILE` | `var/folder.sh` | Folder list for watch/dedupe |
| `FFMPEG_BIN_DIR` | `""` (use `PATH`) | Directory holding `ffmpeg`/`ffprobe` |
| `LOG_LEVEL` | `WARNING` for the logger, `DEBUG` for ffmpeg's `-loglevel` | Verbosity, any casing (`info`, `INFO`, `20`) |
| `LOG_BACKUP_COUNT` | `5` | Rotated log copies |
| `ENV` | — | `development` switches to the relative-path/coloured log format |
| `TRANSCRIBER_MODEL` / `TRANSCRIBER_INITIAL_PROMPT` | `base` / built-in prompt | Transcription |
| `BAIDU_TRANSLATE_*` | — | Keyword translation |

## macOS LaunchAgent

For unattended processing, run the watcher as a LaunchAgent. An example plist lives at `macOS/LaunchAgents/mediakit.plist`.

```sh
# 1. make sure the venv and ffmpeg are in place (see Installation)
# 2. point ProgramArguments at an absolute path to watcher.sh
# 3. load it
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/mediakit.plist

# stop and remove
launchctl bootout gui/$(id -u) macOS/LaunchAgents/mediakit.plist
```

`watcher.sh` activates `.venv` and delegates to `watcher_.sh`; set `ENV` there to switch between `development` and `production`. `watcher_.sh` refuses to start twice, so a leftover process is not duplicated. Key plist fields: `ProgramArguments`, `WorkingDirectory` (project root), `StandardOutPath` / `StandardErrorPath`, and `StartInterval` for periodic runs.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ffmpeg: command not found` / exit 127 | ffmpeg is not bundled — `brew install ffmpeg`, or set `FFMPEG_BIN_DIR` |
| `transcriber CLI not found` | `brew install RedAtman/tap/transcriber`, or skip `save_text` |
| Startup prints `Folder path does not exist, skipping: ...` | stale entries in the folder list; they are skipped, but cleaning them shortens startup |
| `mediakit trim` is rejected | `trim` has no CLI yet (it needs a time range); use the library API `Folder.trim` |
| Watch daemon seems idle right after start | with a few hundred folders, scheduling takes ~95 ms each (~23 s for 224) before all events are live |
| Database or logs vanished after `brew upgrade` | they live in the platform state directory; set `SQLITE_DATABASE` to pin them |
| Nothing is throttled | the throttler only implements macOS and Linux; elsewhere it warns once and runs unthrottled |

Exit codes: `0` success, `1` an action failed, `2` bad arguments (argparse).

## Development

```sh
uv sync
uv run pytest -q                                   # full suite
uv run ruff check --select F401,F841,I . && uv run ruff format --check .
pre-commit run --all-files                         # exactly what CI runs
```

The suite, the lint/format gates and the platform binaries all run in CI on every push and pull request — see the badge above for the current state rather than a count in this file.

Layout: `cli.py` (entry point) → `utils/cli.py` (argument parsing) → `src/schedulers/folder.py` (one scheduler per action) → `base/` (ffmpeg wrappers per media type) → `utils/` (shared: command, db, throttle, progress). `AGENTS.md` documents the architecture, invariants and anti-patterns in detail.

Releases are cut by bumping `[project].version` in `pyproject.toml` and tagging `v<version>`; `.github/workflows/release.yml` re-runs the suite, requires the tag to match the version, then publishes wheels, four platform binaries and the Homebrew formula.

## License

MIT — see [LICENSE](LICENSE).
