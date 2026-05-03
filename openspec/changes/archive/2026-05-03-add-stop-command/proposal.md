## Why

Mediakit's watch mode (`mediakit compress --watch`) runs as a long-lived daemon process. There is currently no way to stop it except by sending raw Unix signals or using `pkill`. A dedicated `mediakit stop` command provides a user-friendly, safe way to shut down the daemon without needing to find the PID manually.

## What Changes

- Add `mediakit stop` CLI action (default: graceful stop — wait for in-flight ffmpeg processes to finish)
- Add `mediakit stop --force` (immediate stop — SIGKILL entire process tree)
- Track running watch instance via PID file at `~/.mediakit/daemon.pid`
- Enhance `WatcherScheduler` to write/clean up PID file and handle SIGTERM with proper drain
- Add `stop` to CLI `mapper_action` and wire it as a `_SimpleScheduler` in `src/schedulers/folder.py`

## Capabilities

### New Capabilities
- `stop-daemon`: Stop a running mediakit watch daemon gracefully or immediately

### Modified Capabilities

<!-- None — this is a brand new command, no existing spec is changing -->

## Impact

- `utils/cli.py` — add `stop` action; add `--force` flag
- `src/schedulers/folder.py` — add `stop = _SimpleScheduler(...)` entry point
- `src/schedulers/watcher.py` — PID file life-cycle; enhanced graceful shutdown
- `~/.mediakit/daemon.pid` — new runtime artifact
- No changes to media processing pipeline or database schema
