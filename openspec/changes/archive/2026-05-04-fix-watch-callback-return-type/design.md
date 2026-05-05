## Context

### Current State

mediakit has two code paths for processing media:

**Non-watch path** (`src/schedulers/folder.py:_compress`):
```
partial(media_compress.core, media)          # middleware scheduler
  → update_state middleware: sets unprocessed=-1
  → _compress middleware: decorator.exception(getattr(self, 'compress'))()
  → wraps dict result in Result(0, data=dict)
  → _callback receives Result object ✅
  → state set to finished(2) ✅
  → file.soft_remove() ✅
```

**Watch path** (`src/schedulers/watcher.py:_feed_existing / _flush_callback`):
```
Folder.run__('compress', medias=[...])
  → getattr(media, 'compress')              # Video.compress directly
  → @timer → @execute → compress()          # returns plain dict
  → {"media":..., "new_file_path":..., "result":...}
  → _batch_callback receives plain dict ❌
  → hasattr(plain_dict, 'data') == False
  → early return — state never updated, file never moved
```

The `Video.compress` method is decorated with `@decorator.timer` and `@decorator.execute`. The `@execute` decorator runs ffmpeg and returns a plain `dict`. The `decorator.exception` class (which wraps results in `Result` objects) is ONLY applied in the middleware chain, not on the method itself.

### Constraints

- The `_batch_callback` in watcher.py was already updated (commit 6518875) to handle `Result` objects with proper state updates and `soft_remove`. The logic is correct — it just never executes because the result type is wrong.
- The non-watch path works correctly and must be preserved unchanged.
- `decorator.execute` and `decorator.exception` are general-purpose and should not be modified for this fix.
- `Folder.run__()` is a generic dispatcher used by multiple actions (compress, scale, trim, etc.) — changing its behavior could affect other callers.

## Goals / Non-Goals

**Goals:**
- Make `_feed_existing` and `_flush_callback` receive `Result` objects (wrapped by `decorator.exception`) so that `_batch_callback` can properly update DB state and move files.
- Unify the watch path with the non-watch path's middleware scheduler pattern.

**Non-Goals:**
- Do NOT modify `decorator.py`, `Folder.run__()`, or `Video.compress()`.
- Do NOT change the `_batch_callback` signature or behavior (it already handles `Result` objects correctly).
- Do NOT add new CLI flags or change the public API.

## Decisions

### Decision: Use middleware scheduler in watch path

**Chosen:** Replace `Folder.run__('compress', medias=medias, ...)` with `media_compress.core` scheduler in both `_feed_existing` and `_flush_callback`.

```python
# Before (broken):
Folder.run__('compress', medias=medias, max_workers=max_workers, callback_list=[_batch_callback])

# After (fixed):
from .media import compress as media_compress
scheduler = media_compress.core
tasks = [functools.partial(scheduler, media) for media in medias]
Folder.run___(tasks=tasks, max_workers=max_workers, callback_list=[_batch_callback])
```

**Rationale:** This is the exact same pattern used by `_compress` in `src/schedulers/folder.py:127-138`. The middleware chain handles:
1. `update_state('compress', unprocessed=-1)` — mark media as processing
2. `decorator.exception(getattr(self, 'compress'))()` — wrap result in `Result` object
3. Return `Result` to callback

**Alternatives considered:**
- **Wrap `getattr(media, 'compress')` with `decorator.exception` manually**: Would work but duplicates middleware logic and doesn't set `unprocessed` state.
- **Modify `Folder.run__()` to apply `decorator.exception`**: Breaks caller independence — not all media methods need exception wrapping.
- **Modify `_batch_callback` to handle dicts too**: Fragile, creates two code paths with different result shapes.

### Decision: Keep existing _batch_callback unchanged

The `_batch_callback` already handles `Result` objects correctly (from commit 6518875). It checks `result.data.get("media")`, `result == 0` for success, and calls `update_state(finished/failed)` + `file.soft_remove()`. No changes needed.

## Risks / Trade-offs

- **[Risk] Media state set to `unprocessed(-1)` twice**: The middleware scheduler sets `unprocessed` before processing. If the file was already scanned as unprocessed, this is a no-op (same value). **Mitigation**: `update_state` in `src/models/media.py` validates the new state — setting `-1` when already `-1` is harmless.

- **[Risk] Task shape change**: `media_compress.core` expects `(self: Video, *args, ctx, **kwargs)`. The `partial(scheduler, media)` pattern passes `media` as `self`, which matches `self: Video`. **Verified**: same pattern used in `folder.py:_compress` without issues.

- **[Trade-off] middleWare scheduler adds one extra function call per task**: The middleware chain executes `update_state → _compress → lambda`. This is negligible compared to ffmpeg runtime (seconds to minutes).
