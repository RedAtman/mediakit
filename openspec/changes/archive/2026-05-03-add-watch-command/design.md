## Context

MediaKit's current processing model is pull-based: `mediakit compress` scans a folder, queries the DB for unprocessed media, and runs compression. The existing `src/file/watcher.py` attempted watchdog integration but has a broken import (`from schedulers import scheduler`) and was never wired into the CLI. The active production watcher (`watcher_.sh`) uses cron-based polling via `var/folder.sh` — wasteful when nothing changes.

The new `watch` command introduces a push-based model: watchdog fires events → debounce + stability check → process via existing compress pipeline.

## Goals / Non-Goals

**Goals:**
- `mediakit watch -f /path` runs as a long-lived foreground process
- Reuse existing compress/media logic (same compression code, same DB, same CPU throttler)
- File stability detection (size + time) to avoid processing in-flight copies
- Debounce burst arrivals (5s calm period) for batch efficiency
- Support `-t`, `-w`, `-c` flags identical to `compress`
- New flags: `--no-recursive` (default: non-recursive), `--no-scan-existing` (default: scan at startup)

**Non-Goals:**
- Not building a general-purpose daemon/background service (use existing LaunchAgent for that)
- Not modifying the existing `compress` scheduler's behaviour
- No cross-host sync or distributed queue

## Decisions

### Decision 1: New scheduler vs extension of existing MiddlewareScheduler chain

**Choice**: New `WatcherScheduler` class in `src/schedulers/watcher.py`, NOT a MiddlewareScheduler.

**Rationale**: MiddlewareScheduler is designed for a linear one-shot chain (config → scan → query → process). A watcher needs an event loop, debounce timer, and long-running Observer. These are fundamentally different execution models. Squeezing a watcher into the middleware pattern would fight it.

**Alternatives considered**:
- MiddlewareScheduler variant with a looping middleware — ruled out (too convoluted, breaks the pattern's contract of `ctx.next()` being called once)
- Embedding watch logic in `_SimpleScheduler` — ruled out (needs more structure than a lambda)
- Extending the existing `compress` middleware chain with a "persistent" mode — ruled out (would couple two concerns)

### Decision 2: Architecture — Observer loop + batch dispatch

```
mediakit watch entry point
│
├── CLI arg parsing (reuse existing create_parser additions)
│
├── [Optional] Phase 1: Scan existing files
│   └── feed_existing(): iterate folder, check DB, collect new media, batch-process
│
├── Phase 2: Watch loop
│   ├── watchdog Observer (non-recursive by default)
│   ├── On created event → FileStabilityTracker (size + 3s stable check)
│   ├── Stable file → DebounceBuffer (5s calm timer → batch dispatch)
│   └── Batch dispatch → TaskManager (reuse from folder.py:run___)
│
├── Signal handling: SIGINT/SIGTERM → graceful shutdown (finish current tasks)
├── CPU throttling: reuse same _coordinator from src/schedulers/folder.py
└── Output: progress bars + periodic log lines (for log files)
```

### Decision 3: DebounceBuffer as a dedicated class

**Choice**: A `DebounceBuffer` class that collects incoming media paths and flushes after 5 seconds of inactivity.

**Design**:
```python
class DebounceBuffer:
    def __init__(self, flush_callback, calm_period=5):
        self.buffer = set()        # deduplicated paths
        self.calm_period = calm_period
        self.flush_callback = flush_callback
        self._timer = None

    def add(self, path):
        self.buffer.add(path)
        self._reset_timer()  # restart the 5s countdown

    def _flush(self):
        paths = list(self.buffer)
        self.buffer.clear()
        self.flush_callback(paths)
```

**Rationale**: Simpler than a debounce-per-file approach. Grouping arrivals is more efficient for TaskManager batching.

### Decision 4: File stability detection

Two-layer check, applied per-path before adding to DebounceBuffer:
1. **Size stability**: sample file size every 1s, emit when size unchanged for 3 consecutive samples
2. **Timeout fallback**: max 30s wait, then process anyway (handles stalled connections or edge cases)

Uses a simple per-path `dict` tracking last size + stable counter.

### Decision 5: CPU throttler sharing

The global `_coordinator` is already module-level in `src/schedulers/folder.py`. The new `src/schedulers/watcher.py` will import and share it rather than creating a new coordinator instance. This is safe because:
- `_coordinator` has no dependency on the middleware chain
- `CommandExecutor.coordinator` is already set globally

### Decision 6: CLI argument mapping

Reuse existing argparse additions rather than creating a new parser:

| Flag | Reuse | Notes |
|------|-------|-------|
| `-f`/`--folder` | Yes | Required for watch, same meaning |
| `-t`/`--type` | Yes | `video`, `audio`, `image` |
| `-w`/`--max_workers` | Yes | Thread pool size |
| `-c`/`--cpu-limit` | Yes | CPU throttle limit |
| (new) `--no-recursive` | New | Default: false (recursive=no) |
| (new) `--no-scan-existing` | New | Default: false (scan=yes) |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Incomplete file race**: Observer fires `on_created` before write completes | Two-layer stability check (size + time + timeout) |
| **Debounce delay**: 5s wait means files aren't processed instantly | Debounce is for bursts. Single files will flush after 5s. Acceptable for batch media processing. |
| **Memory leak**: DebounceBuffer fills up if no calm period | Add a max-flush-interval (e.g., 60s hard timeout) as safety valve |
| **Observer death**: watchdog Observer silently stops | Main thread polls Observer.is_alive() every 30s and restarts if dead |
| **Folder deleted while watching**: path disappears | Catch FileNotFoundError, log warning, continue loop |
| **CPU throttler scope**: `_coordinator` is module-level in folder.py, creating coupling | Acceptable coupling — both schedulers serve the same process lifetime |

### Decision 7: Folder file support (multi-folder)

**Choice**: A `--folder-file` flag for reading multiple folder paths from a text file.

**Design**:
- `--folder-file` long flag; `-f` remains single-folder (backward compat)
- `CONFIG.WATCH_FOLDER_FILE` defaults to `var/folder.sh` resolved from project root
- Fallback: `CONFIG.MEDIA_FILE_FOLDER` when default file does not exist
- Lines stripped, `#` comments skipped, blanks skipped
- One `Observer.schedule()` per valid path, all sharing a single Observer
- Non-existent paths logged as warning, skipped

**Implemented in**: `src/schedulers/watcher.py` (`_parse_folder_file`, `_setup_multi_observer`, `core()` path resolution)

## Open Questions

- None confirmed. All major design decisions resolved during exploration.
