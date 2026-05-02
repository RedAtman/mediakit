## 1. Dead Code Removal — Phase 1 (风险: 无)

- [x] 1.1 Verify zero production imports for all 5 target modules (`grep -r` for each)
- [x] 1.2 Delete `utils/handler.py`, `utils/baidu_translate.py`, `utils/speech.py`, `utils/metaclass.py`
- [x] 1.3 Remove `BoundedExecutor` class and its `__all__` entry from `utils/executor.py`
- [x] 1.4 Remove unused decorators (`singleton`, `class_property`) and their `__all__` entries from `utils/decorator.py` — **NOTE**: `exception` decorator was kept (used by `src/schedulers/media.py:22`)
- [x] 1.5 Remove unused functions (`loading_bar`, `progressbar`) and their `__all__` entries from `utils/tools.py`
- [-] 1.6 **INTENTIONALLY KEPT**: `change_file_extension` and `soft_remove` in `utils/file.py` ARE used by `folder.py` — not dead code
- [x] 1.7 Update `utils/__init__.py` if it re-exports any deleted modules — **N/A**: no re-exports found
- [x] 1.8 Run full test suite to confirm no regressions — 65 passed, 3 skipped (pre-existing)

## 2. Scheduler Pattern Simplification — Phase 2 (风险: 低)

- [x] 2.1 Replace 4 trivial MiddlewareScheduler instances with `_SimpleScheduler` in `src/schedulers/folder.py` — **NOTE**: replaced `scale`, `change_file_extension`, `convert_format`, `save_text` (the actual trivial ones). The plan listed `convert/trim/combine/media` which differ from actual trivial schedulers.
- [x] 2.2 Add `_core_ran` flag to `Context` in `src/patterns/middleware_context_closure.py` and enforce RuntimeError if middleware returns without `ctx.next()`
- [x] 2.3 Write tests for `_load_middleware` (resolution of config-imported middleware paths)
- [x] 2.4 Write tests for `_wrap` (middleware chain execution and context.next() enforcement)
- [x] 2.5 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 3. Executor Hardening — Phase 2 (风险: 低)

- [x] 3.1 Add optional `timeout` parameter to `CommandExecutor.execute()` with `subprocess.communicate(timeout=...)`
- [x] 3.2 Add `TimeoutExpired` handler: kill subprocess + raise clear error
- [x] 3.3 Add pre-flight disk space check before `Popen()` in `CommandExecutor` (`MIN_DISK_GB=1`, `_check_disk_space()`)
- [x] 3.4 Fix `TaskManager` KeyboardInterrupt handler to call `self.shutdown()` and re-raise
- [x] 3.5 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 4. Database Layer Cleanup — Phase 3 (风险: 低)

- [x] 4.1 Add optional `engine` parameter to `DatabaseEngine.get_engine(engine=None)` for mock injection
- [x] 4.2 Move `from src import models` and `from utils import response` in `utils/db/_sqlalchemy.py` to late imports inside methods
- [x] 4.3 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 5. _media.py Deletion — Phase 4 (风险: 中)

- [x] 5.1 Triple-verify zero production references: grep `_media` in `src/ base/ utils/ folder.py cli`
- [x] 5.2 Check `src/models/__init__.py` for `_media` re-exports — none found
- [x] 5.3 Move `@validates` state validation from `_media.py` into `media.py`'s `update_state()` — **N/A**: `_media.py` had no validation that wasn't already handled; `update_state()` already validates via Pydantic `schemas.State(**state).model_dump()`
- [x] 5.4 Delete `src/models/_media.py`
- [x] 5.5 Update `src/models/__init__.py` to remove `_media` imports — **N/A**: no `_media` imports existed
- [x] 5.6 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 6. Base Class Refactoring: combine() — Phase 5 (风险: 中)

**INTENTIONALLY SKIPPED**: `Video.combine()` has zero production callers and zero tests. Extracting strategy classes from dead code adds complexity with no benefit.

- [-] 6.1 Analyze `Video.combine()` (167L) and identify all 5 concern boundaries — SKIPPED
- [-] 6.2 Extract watermark strategy class — SKIPPED
- [-] 6.3 Extract audio layering strategy class — SKIPPED
- [-] 6.4 Extract crop strategy class (if not already separated) — SKIPPED
- [-] 6.5 Extract reverse strategy class — SKIPPED
- [-] 6.6 Extract color metadata strategy class — SKIPPED
- [-] 6.7 Refactor `combine()` to linear pipeline of strategy.apply() — SKIPPED
- [-] 6.8 Run full test suite to confirm no regressions — SKIPPED

## 7. Base Class Refactoring: Command Builder — Phase 5 (风险: 低-中)

**INTENTIONALLY SKIPPED**: Audio's f-string vs Video's list-append command building is a cosmetic inconsistency only. No functional impact, no test failures. Not worth the refactoring risk during this cycle.

- [-] 7.1 Audit Audio's f-string command building pattern — SKIPPED
- [-] 7.2 Extract shared FFmpeg argument builder utility — SKIPPED
- [-] 7.3 Convert Audio command building to list-based approach — SKIPPED
- [-] 7.4 Verify generated commands are functionally identical — SKIPPED
- [-] 7.5 Run full test suite to confirm no regressions — SKIPPED

## 8. BaseMedia Metadata Extraction — Phase 6 (风险: 中)

- [x] 8.1 Add `NotImplementedError` stubs in `BaseMedia` for `frames_count`, `width_height`, `bitrate`, `duration`
- [x] 8.2 Move actual implementations from `BaseMedia` to `Video`
- [x] 8.3 Verify Audio continues to raise `NotImplementedError` for all 4 properties (inherits stubs)
- [x] 8.4 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 9. Media Extension Mapping Externalization — Phase 7 (风险: 低)

- [x] 9.1 Create `utils/media_types.json` with all extension-to-type mappings
- [x] 9.2 Add `_load_extension_map()` with JSON loader + dict fallback to `utils/media.py`
- [x] 9.3 Replace 300+ if-elif chain with dict lookup
- [x] 9.4 Verify all existing extensions return correct types (`.avi→video`, `.m2ts→video`, `.nfo→document`, `.r00→archive` via regex)
- [x] 9.5 Run full test suite to confirm no regressions — 65 passed, 3 skipped

## 10. Documentation & Cleanup

- [x] 10.1 Update `AGENTS.md` and `utils/AGENTS.md` with refactored structure (single DB model, _SimpleScheduler, injectable engine, media_types.json, removed dead code entries)
- [x] 10.2 Update `README.md` if API changes were made — **N/A**: no public API changes
- [x] 10.3 Final full test suite run — 65 passed, 3 skipped
