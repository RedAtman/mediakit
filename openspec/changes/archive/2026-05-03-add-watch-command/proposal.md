## Why

MediaKit currently processes media files only on-demand via `mediakit compress`, requiring manual invocation or cron-based polling (`watcher_.sh`). When users want to monitor a folder for new media files and process them automatically as they arrive, there is no built-in way — they must either run `compress` periodically (wasteful when nothing changes) or set up external file watchers. Adding a `mediakit watch` command solves this by providing a first-class, event-driven watch mode that processes new media files in real-time.

## What Changes

- Add `--watch` flag to existing CLI commands (`compress`, `trim`, `scale`, `save_text`): `mediakit compress --watch -f /path` — event-driven, long-running process monitoring a folder
- Add `WatcherScheduler` class in `src/schedulers/watcher.py` — routes via `cli.py:main()` when `args.watch` is True
- Integrate watchdog's `Observer` for filesystem events
- Reuse existing media type detection, DB state tracking (`get_or_create`), and compression logic via `Folder.run__(action, ...)`
- Add debounce mechanism: batch-dispatch files after a calm period (5 seconds without new events)
- Add file stability detection: wait for file size to stabilize before processing
- Processed files are soft-removed (same behaviour as `compress` callback)
- Add CLI arguments: `--no-recursive` (default: no recursion), `--no-scan-existing` (default: scan existing files at startup), `--folder-file` for multi-folder paths, `--watch` flag
- Compatible with existing `-t` (type), `-w` (workers), `-c` (cpu-limit) arguments
- Add `CONFIG.WATCH_FOLDER_FILE` defaulting to `var/folder.sh` with fallback to `CONFIG.MEDIA_FILE_FOLDER`
- Remove initial `watch` subcommand and `-a`/`--action` design after user feedback — replaced with `--watch` flag on existing actions

## Capabilities

### New Capabilities
- `folder-watch`: Event-driven folder monitoring and auto-processing of new media files

### Modified Capabilities

<!-- No existing capabilities have requirement changes at the spec level. -->

## Impact

- **New file**: `src/schedulers/watcher.py` — watch scheduler with Observer-based event loop
- **Modified**: `src/file/watcher.py` — refactor existing FolderWatcher to support the new scheduler (or replace it)
- **Modified**: `cli.py` — register `watch` in the action mapper and route to the new scheduler
- **Modified**: `utils/cli.py` — add `watch` to `mapper_action` and new arguments
- **New optional file**: `config` may gain `WATCH_*` environment variables for defaults
- **Dependencies**: `watchdog` already in dependencies
- **No new external dependencies required**
