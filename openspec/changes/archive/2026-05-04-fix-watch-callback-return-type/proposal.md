## Why

Watch mode (`--watch`) has three bugs that prevent it from working correctly: state stuck at progress float instead of `finished=2`, files not moved to `.removed/` after processing, and recursive subdirectory watching active by default contrary to spec. The root cause of the state + file-move bugs is a return-type mismatch: the watch path calls `Video.compress()` directly through `Folder.run__()`, which returns a plain `dict`, but `_batch_callback` expects a `response.Result` object. The callback silently returns without updating state or moving files.

## What Changes

- **Fix watch path to use middleware scheduler**: Replace `Folder.run__('compress', ...)` in `_feed_existing` and `_flush_callback` with `media_compress.core` scheduler (matching the non-watch path in `folder.py:_compress`). This ensures results are wrapped in `response.Result` objects by `decorator.exception` before reaching `_batch_callback`.
- **Remove unused imports** from watcher.py if any after refactor.
- **Recursion fix already committed** (6f2c024): `--no-recursive` renamed to `--recursive`, default changed to non-recursive. Requires `uv tool install --reinstall .` to deploy.

## Capabilities

### New Capabilities
- `watch-state-management`: Ensures watch-mode processing correctly updates DB state to `finished(2)` / `failed(-2)` and moves processed files to `.removed/` after completion.

### Modified Capabilities
None — this is a bugfix aligning implementation with existing spec behavior defined in the archived `2026-05-03-add-watch-command/specs/folder-watch`.

## Impact

- `src/schedulers/watcher.py`: `_feed_existing()` and `_flush_callback()` — replace `Folder.run__()` calls with middleware scheduler
- `src/schedulers/media.py`: `compress.core` scheduler — already correct, no changes needed
- `_batch_callback`: already has correct state-update and soft_remove logic (from 6518875), just never reached before
- `file.soft_remove()` path: unchanged, already works correctly
- No CLI or public API changes
