## Context

The watcher daemon (`WatcherScheduler` in `src/schedulers/watcher.py`) currently reads its folder list from `WATCH_FOLDER_FILE` (or `--folder-file`) **exactly once** during `core()`. The parsed paths are passed to `_setup_observer()` or `_setup_multi_observer()`, which create a watchdog `Observer` and schedule watches via `observer.schedule(handler, path)`. After that, `_run_event_loop()` runs a simple keepalive loop (`sleep(1)`, check if observer is alive). No mechanism exists to re-read the config file or add/remove watches at runtime.

The watchdog library's `Observer` (on macOS: `FSEventsObserver`) supports dynamic operations:
- `observer.schedule(handler, path, recursive=bool)` → returns `ObservedWatch`
- `observer.unschedule(watch)` → removes a watch
- Both are thread-safe (internal `self._lock`)

No external library changes are needed.

## Goals / Non-Goals

**Goals:**
- Detect modifications to `WATCH_FOLDER_FILE` (resolved at startup) without restarting the daemon
- Compute diff of paths (additions, removals) since last read
- `observer.schedule()` for newly added directories — they immediately begin receiving file events
- `observer.unschedule()` for removed directories — they stop receiving file events
- Call `_feed_existing()` on newly added directories so pre-existing media files get processed
- Handle edge cases: file temporarily missing, malformed content, invalid directories
- All state changes logged at `INFO` level for observability

**Non-Goals:**
- Real-time (<1s) detection of config changes — 5s polling latency is acceptable
- Hot-reload of other config values (CPU_LIMIT, MAX_WORKERS, etc.) — only folder paths
- GUI or signal-based config reload — polling `mtime` is sufficient
- Removal of in-flight processing when a directory is removed — only future events are stopped

## Decisions

### Decision 1: Polling mtime vs. watchdog-based file watching

The config file could be watched with a second watchdog `Observer` on its parent directory. However:

| Aspect | Watchdog on config file | Polling mtime |
|--------|------------------------|---------------|
| Latency | ~instant | ~5s |
| Complexity | Need to separate config events from media events (different handler) | Simple mtime check in existing loop |
| Thread safety | Works (already in Observer thread) | Works (main thread in `_run_event_loop`) |
| Edge cases | File rename during write, temp files | `getmtime` is atomic |
| Code footprint | ~40 lines + new handler class | ~20 lines in `_run_event_loop` |

**Chosen: Polling mtime.** The complexity of routing config-file events through the existing event handler outweighs the latency benefit. Config changes are administrative actions, not time-sensitive. Polling every 5 seconds in the existing `_run_event_loop` adds minimal code and zero new concurrency concerns.

### Decision 2: Store handler reference for dynamic schedule()

Currently `_setup_observer` and `_setup_multi_observer` create `_WatchEventHandler` locally and never expose it. For dynamic `observer.schedule(handler, new_path)` calls, we need a reference to the handler. Rather than refactoring both methods, store `self._handler` after setup completes using the existing handler instance. This minimizes changes to existing code paths.

### Decision 3: Diff logic location

The diff computation (new paths − old paths, old paths − new paths) lives in a new private method `_check_config_file_changes()` called from `_run_event_loop()`. This keeps the core loop responsible for lifecycle and the config change logic self-contained.

### Decision 4: New directory catch-up

When a new directory is added via config file change, the watcher immediately calls `_feed_existing()` on it — same as the startup scan. This ensures pre-existing media files in the newly added directory are processed without waiting for new file events.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Config file write is in progress when polled (partial content) | `_parse_folder_file` reads atomically (`Path.read_text()`), but partial writes could lose entries. Mitigation: if parsing fails (exception), keep current state and log a warning. The next poll (5s later) will catch the complete file. |
| Malformed config after edit (e.g., non-UTF-8 content) | Wrap `_parse_folder_file()` in try/except; on failure, log warning and preserve current watched set. |
| Config file deleted at runtime | `os.path.isfile()` check before reading. If missing, log info and keep current watches. If re-appears, re-read and re-sync. |
| User removes a directory with in-flight processing | `unschedule()` only stops new event notifications. Already-queued media files in the debounce buffer or currently being processed are unaffected. |
| `os.path.getmtime()` resolution on some filesystems | HFS+/APFS has 1-second mtime granularity. This is fine — 5s polling interval is well above the granularity floor. |
| Race: config changes trigger `_feed_existing` while media is being processed for the same path | `_feed_existing` reads unprocessed media from the DB (state = -1 / unprocessed) via `get_query_statement('QUERY_UNPROCESSED')`. Already-queued or in-flight media will have non-unprocessed states, so they won't be double-processed. |
