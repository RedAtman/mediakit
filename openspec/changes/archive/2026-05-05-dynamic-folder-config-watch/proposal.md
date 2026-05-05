## Why

watch mode currently reads `WATCH_FOLDER_FILE` (default `var/folder.sh`) **once** at startup. Any subsequent additions to that file — new directories the user wants to monitor — require stopping and restarting the entire daemon. This is friction for a long-running service that's expected to run unattended for days or weeks. The user should be able to add new watched directories by simply editing a text file, with zero downtime.

## What Changes

- The watcher daemon monitors `WATCH_FOLDER_FILE` (or `--folder-file`) for modifications at runtime
- When new directory entries are detected in the config file, they are automatically added to the watchdog Observer's watch list
- When entries are removed from the config file, their corresponding watches are removed
- Newly added directories are scanned for existing unprocessed media files (same as startup behavior)
- No restart required — the change is seamless and logged

## Capabilities

### New Capabilities
- `config-file-watch`: Runtime detection of changes to the WATCH_FOLDER_FILE configuration, with automatic diff-based addition/removal of watched directories

### Modified Capabilities
- *(none — no existing spec-level behavior is changing)*

## Impact

- **File**: `src/schedulers/watcher.py` — `WatcherScheduler` class. Add config file polling, path tracking state, and new `_check_config_file_changes()` method. Modify `_run_event_loop()` to include periodic config checks.
- **No API changes**: CLI interface, env vars, and existing method signatures remain unchanged.
- **No dependency changes**: Uses existing `os.path.getmtime()` and watchdog `Observer.schedule()`/`unschedule()`.
- **Tests**: `tests/test_scheduler_watcher.py` — new test cases for dynamic add/remove, mtime change detection, and edge cases (malformed config, missing file).
