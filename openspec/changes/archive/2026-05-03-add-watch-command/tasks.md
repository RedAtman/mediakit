## 1. CLI Integration

- [x] 1.1 Add `--no-recursive` and `--no-scan-existing` arguments to `create_parser()` in `utils/cli.py`
- [x] 1.2 Add `--folder-file` argument for multi-folder path file; `--watch` store_true flag
- [x] 1.3 Wire watch in `cli.py:main()` — `getattr(folder.actions, args.action).core()` when `args.watch`
- [x] 1.3b **Refactor**: Removed `watch` subcommand and `-a`/`--action` flag. `--watch` flag on existing actions (`compress --watch`, `trim --watch`, `scale --watch`)

## 2. DebounceBuffer Utility

- [x] 2.1 Implement `DebounceBuffer` class in `src/file/debounce.py`
- [x] 2.2 Buffer stores deduplicated paths (`set`), flushes to callback after `calm_period` seconds of no new adds
- [x] 2.3 Implement max-flush-interval safety valve (60s hard timeout)

## 3. FileStabilityTracker Utility

- [x] 3.1 Implement per-path size stability detection (size unchanged for 3 consecutive 1s samples → stable)
- [x] 3.2 Implement 30s timeout fallback (process anyway if size keeps changing)
- [x] 3.3 Wire stability check into the event pipeline before adding to DebounceBuffer

## 4. WatcherScheduler

- [x] 4.1 Create `src/schedulers/watcher.py` with `WatcherScheduler` class
- [x] 4.2 Implement `core()` entry point: parse args, init Observer, run event loop
- [x] 4.3 Implement startup phase: optional scan of existing files via DB `get_or_create` (default: enabled, gated by `--no-scan-existing`)
- [x] 4.4 Implement watch phase: Observer → stability check → DebounceBuffer → batch dispatch
- [x] 4.5 Implement batch dispatch using `Folder.run___` / TaskManager (reuse existing parallel execution)
- [x] 4.6 Implement `_batch_callback` for processed files: soft_remove on success
- [x] 4.7 Import and share `_coordinator` from `src/schedulers/folder.py` for CPU throttling
- [x] 4.8 Support `-t`/`--type` and `-w`/`--max_workers` and `-c`/`--cpu-limit` from kwargs
- [x] 4.9 Implement SIGINT/SIGTERM handler: finish in-progress tasks, then exit

## 5. Observer Health Monitoring

- [x] 5.1 Implement periodic `Observer.is_alive()` check every 30s in the main loop
- [x] 5.2 Implement Observer restart logic

## 6. Progress and Logging

- [x] 6.1 Print status banner on start: "Watching /path for new media files..."
- [x] 6.2 Print INFO logs on file events: "File event detected: {type} {path}"
- [x] 6.3 Print batch completion log: "Watch session ended."
- [x] 6.4 Reuse existing progress bar from `utils/progress.py` per-task (see pre-existing pydantic ValidationError when ffprobe frame count < ffmpeg frames → progress > 200%)

## 7. Refactor Existing Code

- [x] 7.1 Remove broken `src/file/watcher.py` (was untracked by git)
- [x] 7.2 Apply event-driven components (`DebounceBuffer`, `FileStabilityTracker`) as standalone utility modules

## 8. Testing

- [x] 8.1 Write unit tests for `DebounceBuffer` (flush timing, dedup, max-flush-interval)
- [x] 8.2 Write unit tests for `FileStabilityTracker` (stable detection, timeout)
- [x] 8.3 Write tests for `WatcherScheduler.core()` with mocked Observer (13 tests: observer setup, event loop, signal handler, dispatch, callback, multi-observer)
- [x] 8.4 Write tests for CLI argument parsing (watch flags, --watch, --folder-file, --no-recursive, --no-scan-existing)
- [x] 8.5 Write tests for SIGINT graceful shutdown, modified/moved events, output dir exclusion, non-media handling

## 9. Folder File Support

- [x] 9.1 Add `WATCH_FOLDER_FILE` class attribute to config.py with default path resolved via `os.path.dirname(__file__)` to `var/folder.sh`
- [x] 9.2 Add `--folder-file` argument to CLI parser in `utils/cli.py`
- [x] 9.3 Implement `_parse_folder_file()` in `src/schedulers/watcher.py`: read file, strip lines, skip `#` comments and blanks
- [x] 9.4 Implement folder resolution logic in `WatcherScheduler.core()`: prefer explicit `--folder-file`, fall back to `CONFIG.WATCH_FOLDER_FILE`, fall back to `CONFIG.MEDIA_FILE_FOLDER` when default file missing
- [x] 9.5 Implement path validation: skip nonexistent paths with warning, log hint when all paths invalid
- [x] 9.6 Implement multiple observer schedule creation: one `observer.schedule()` call per valid folder path
- [x] 9.7 Ensure `--no-recursive` and `--no-scan-existing` apply uniformly to all scheduled paths
- [x] 9.8 Write tests: folder file parsing, path resolution order, nonexistent path warning, multi-observer schedules

## 10. Post-Archive Iterations (Bug Fixes & Refinements)

- [x] 10.1 **media.core bug**: `partial(media.core)` crashed — replaced with `Folder.run__(action, ...)` via `core()` action kwarg
- [x] 10.2 **Feedback loop**: output files in `_[...]` subdirs and `.removed/` re-processed — `dispatch()` excludes paths with `/_[` or `/.removed/`
- [x] 10.3 **Dict result handling**: `_batch_callback` expected `Result` objects but `@decorator.execute` returns dicts — handles both; wrapped `future.result()` in try/except for task-exception resilience
- [x] 10.4 **Non-media ERROR**: `NotMediaException` from `folder.MEDIA_CLS()` propagated through `DebounceBuffer._flush` as ERROR — now caught, logged as warning, skipped
- [x] 10.5 **Event coverage**: dispatch only handled `'created'` — Finder needs `'modified'` (copyfile) and `'moved'` (temp-file-rename). All three handled; `moved` uses `dest_path`
- [x] 10.6 **Startup visibility**: added INFO logs for watched folder, running state, and per-file events
- [x] 10.7 **`--watch` flag refactor**: removed `watch` subcommand and `-a`/`--action` flag after user feedback ("参数action和--action是设计重复"). Replaced with `--watch` store_true flag on existing commands: `mediakit compress --watch`, `mediakit trim --watch`, etc.
