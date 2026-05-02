## Why

The codebase has accumulated significant technical debt across all layers after rapid feature development. A systematic architecture audit (5 parallel agents + manual verification) revealed: ~1100 lines of dead code, zero-tested middleware patterns masking trivial dispatch, LSP violations in the base class hierarchy, stalled dual-model migration, missing subprocess safeguards, and over-engineered abstractions serving single use cases. These issues compound — each new feature becomes harder to add, and bugs in the throttling/fix cycle showed that even working code is fragile when the foundation is unclear. This refactor pays down the debt in risk-ordered increments so the codebase becomes easier to understand, test, and extend.

## What Changes

### Layer 1: Dead Code Removal (风险: 无)
- Delete `utils/handler.py` (7L stub, unused)
- Delete `utils/baidu_translate.py` (58L, unused)
- Delete `utils/speech.py` (153L, unused — only 1 of 3 translation implementations used)
- Delete `utils/metaclass.py` (29L, Singleton metaclass unused)
- Delete `BoundedExecutor` class from `utils/executor.py` (unused, `TaskManager` is the active executor)
- Remove unused decorators from `utils/decorator.py`: `singleton`, `exception`, `class_property`
- Remove unused functions from `utils/tools.py`: `loading_bar`, `progressbar`
- Remove unused functions from `utils/file.py`: `change_file_extension`, `soft_remove`
- Strip stale `__all__` entries where needed

### Layer 2: Scheduler Pattern Simplification (风险: 低)
- Replace 4 trivial `MiddlewareScheduler` instances (1 middleware + identity core) with plain function calls
- Add runtime `ctx.next()` enforcement in the middleware context — detect silent chain termination
- Add tests for the pattern itself (`_load_middleware`, `_wrap`, `Context` contract)

### Layer 3: Executor Hardening (风险: 低)
- Add timeout parameter to `CommandExecutor.execute()` via `subprocess.communicate(timeout=N)`
- Add disk space check before `Popen()` — fail fast if insufficient space
- Fix `TaskManager` KeyboardInterrupt handler to call `shutdown()` (prevents semaphore leak on Ctrl+C)

### Layer 4: Database Layer Cleanup (风险: 中)
- Make `DatabaseEngine` injectable — remove singleton pattern that prevents mock injection in tests
- Delete `src/models/_media.py` after verifying zero production imports
- Fix layer violation in `utils/db/_sqlalchemy.py` (`from src import models`)

### Layer 5: Base Class Refactoring (风险: 中)
- Extract video-specific metadata properties (`frames_count`, `width_height`, `bitrate`, `duration`) from `BaseMedia` into `Video`, leaving `NotImplementedError` stubs in `BaseMedia`
- Break up `Video.combine()` (167L, 5 concerns) into focused strategy classes
- Unify FFmpeg command building (Audio uses f-strings, Video uses list append — extract shared builder)

### Layer 6: Media Extension Mapping (风险: 低-中, 纯机械操作)
- Extract 300+ extension if-elif chain from `utils/media.py` (472L) to external JSON/YAML data file
- Add data file loader with in-memory dict fallback for backward compatibility

## Capabilities

### New Capabilities
- `scheduler-pattern`: Middleware/scheduler dispatch architecture — context chain enforcement, trivial dispatcher simplification, and pattern tests
- `executor-safety`: Subprocess execution safeguards — configurable timeout, pre-flight disk space check, proper signal cleanup
- `dead-code-sanitization`: Systematic removal of unused modules, classes, and functions across the utils layer
- `base-media-model`: Core media class hierarchy — video/audio metadata boundaries, command builder, `combine()` decomposition
- `db-layer`: Database engine lifecycle and model management — injectable engine, unified state machine, dual-model migration completion
- `media-type-registry`: Externalized media type detection — data-driven extension-to-type mapping

### Modified Capabilities
_(none — no existing specs are changing behavior)_

## Impact

- `base/media.py` — abstract property stubs added, interface unchanged
- `base/video.py` — `combine()` internally refactored, public API unchanged
- `base/audio.py` — unaffected by metadata changes (already raising NotImplementedError)
- `src/patterns/middleware_context_closure.py` — `ctx.next()` enforcement added
- `src/schedulers/folder.py` — 4 trivial schedulers replaced with direct calls
- `src/db.py` — engine initialization made injectable
- `src/models/_media.py` — deleted entirely
- `src/schemas.py` — state validation consolidated (moved from _media.py)
- `utils/command.py` — timeout + disk check added
- `utils/executor.py` — BoundedExecutor removed, TaskManager KeyboardInterrupt fix
- `utils/media.py` — extension mapping extracted to data file, if-elif chain replaced with dict lookup
- `utils/decorator.py` — 3 unused decorators removed
- `utils/tools.py` — 2 unused functions removed
- `utils/file.py` — 2 unused functions removed
- `utils/db/_sqlalchemy.py` — import moved to late binding
- 5 files deleted entirely (handler.py, baidu_translate.py, speech.py, metaclass.py, _media.py)
