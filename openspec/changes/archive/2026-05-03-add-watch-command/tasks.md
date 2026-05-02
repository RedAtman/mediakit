## 1. CLI Integration

- [ ] 1.1 Add `watch` to `mapper_action` in `utils/cli.py`
- [ ] 1.2 Add `--no-recursive` and `--no-scan-existing` arguments to `create_parser()` in `utils/cli.py`
- [ ] 1.3 Wire `watch` in `cli.py` main dispatch (reuses `getattr(folder, args.action)` pattern — just needs `src.schedulers.folder.watch` to exist)

## 2. DebounceBuffer Utility

- [ ] 2.1 Implement `DebounceBuffer` class in `src/file/watcher.py` (or new `src/file/debounce.py`)
- [ ] 2.2 Buffer stores deduplicated paths (`set`), flushes to callback after `calm_period` seconds of no new adds
- [ ] 2.3 Implement max-flush-interval safety valve (60s hard timeout)

## 3. FileStabilityTracker Utility

- [ ] 3.1 Implement per-path size stability detection (size unchanged for 3 consecutive 1s samples → stable)
- [ ] 3.2 Implement 30s timeout fallback (process anyway if size keeps changing)
- [ ] 3.3 Wire stability check into the event pipeline before adding to DebounceBuffer

## 4. WatcherScheduler

- [ ] 4.1 Create `src/schedulers/watcher.py` with `WatcherScheduler` class
- [ ] 4.2 Implement `core()` entry point: parse args, init Observer, run event loop
- [ ] 4.3 Implement startup phase: optional scan of existing files via DB `get_or_create` (default: enabled, gated by `--no-scan-existing`)
- [ ] 4.4 Implement watch phase: Observer → stability check → DebounceBuffer → batch dispatch
- [ ] 4.5 Implement batch dispatch using `Folder.run___` / TaskManager (reuse existing parallel execution)
- [ ] 4.6 Implement `_callback` for processed files: soft_remove on success
- [ ] 4.7 Import and share `_coordinator` from `src/schedulers/folder.py` for CPU throttling
- [ ] 4.8 Support `-t`/`--type` and `-w`/`--max_workers` and `-c`/`--cpu-limit` from kwargs
- [ ] 4.9 Implement SIGINT/SIGTERM handler: finish in-progress tasks, then exit

## 5. Observer Health Monitoring

- [ ] 5.1 Implement periodic `Observer.is_alive()` check every 30s in the main loop
- [ ] 5.2 Implement Observer restart logic

## 6. Progress and Logging

- [ ] 6.1 Print status banner on start: "Watching /path for new media files..."
- [ ] 6.2 Print batch processing log lines: "[timestamp] Processing N files..."
- [ ] 6.3 Print batch completion log lines: "[timestamp] Finished processing N files (S succeeded, F failed)"
- [ ] 6.4 Reuse existing progress bar from `utils/progress.py` per-task

## 7. Refactor Existing Code

- [ ] 7.1 Clean up or remove broken `src/file/watcher.py` import (`from schedulers import scheduler`)
- [ ] 7.2 Apply event-driven components (`DebounceBuffer`, `FileStabilityTracker`) into the module as reusable utilities

## 8. Testing

- [ ] 8.1 Write unit tests for `DebounceBuffer` (flush timing, dedup, max-flush-interval)
- [ ] 8.2 Write unit tests for `FileStabilityTracker` (stable detection, timeout)
- [ ] 8.3 Write integration test for `WatcherScheduler.core()` with mocked Observer
- [ ] 8.4 Write test for CLI argument parsing with new flags
- [ ] 8.5 Write test for SIGINT graceful shutdown

## 9. Folder File Support

- [ ] 9.1 Add `WATCH_FOLDER_FILE` class attribute to config.py with default path resolved via `os.path.dirname(__file__)` to `var/folder.sh`
- [ ] 9.2 Add `--folder-file` argument to the watch parser in `utils/cli.py`
- [ ] 9.3 Implement `_parse_folder_file()` in `src/schedulers/watcher.py`: read file, strip lines, skip `#` comments and blanks
- [ ] 9.4 Implement folder resolution logic in `WatcherScheduler.core()`: prefer explicit `--folder-file`, fall back to `CONFIG.WATCH_FOLDER_FILE`, fall back to `CONFIG.MEDIA_FILE_FOLDER` when default file missing
- [ ] 9.5 Implement path validation: skip nonexistent paths with warning, log hint when all paths invalid
- [ ] 9.6 Implement multiple observer schedule creation: one `observer.schedule()` call per valid folder path
- [ ] 9.7 Ensure `--no-recursive` and `--no-scan-existing` apply uniformly to all scheduled paths
- [ ] 9.8 Write tests: folder file parsing, path resolution order, nonexistent path warning, multi-observer schedules
