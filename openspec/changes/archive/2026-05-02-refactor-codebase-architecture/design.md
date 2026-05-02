## Context

The codebase was built iteratively with TDD-driven rapid feature additions, resulting in accumulated technical debt across 5 architectural layers. A parallel exploration (5 agents + manual cross-validation) mapped the full architecture and identified:

- **~1100 lines of dead code** in utils/ (unused modules, orphaned abstractions, stale functions)
- **4 trivial MiddlewareScheduler instances** that are one-middleware wrappers around identity functions — the pattern is over-engineered for its actual usage
- **Zero tests** for the scheduler pattern itself (`_load_middleware`, `_wrap`, `Context` contract)
- **LSP violation** in BaseMedia: video-specific properties (`frames_count`, `width_height`, etc.) defined as abstract on a base class that also serves Audio
- **Hotspot**: `Video.combine()` at 167L handling 5 independent concerns (watermark, audio, crop, reverse, color metadata)
- **Stalled dual-model migration**: `_media.py` (SQLModel, 105L) has zero production imports — the SQLAlchemy `media.py` (169L) is the real model
- **Non-injectable DatabaseEngine**: `@classmethod @property @cache` singleton prevents mock injection in tests
- **Layer violations**: `utils/db/_sqlalchemy.py` imports `src.models.Base`, `utils/progress.py` imports `src.models`
- **Missing subprocess safeguards**: No timeout on `communicate()`, no disk space check before ffmpeg launch
- **Over-engineered translation layer**: 3 implementations (Translator, BaiduTranslator, VoiceAssistant) for 1 active use case
- **Inline data**: `utils/media.py` (472L) has 300+ extension-to-type mappings in an if-elif chain

This design covers all identified issues, ordered by risk so high-confidence deletions can proceed in parallel with more carefully scoped refactoring.

## Goals / Non-Goals

**Goals:**
- Remove zero-risk dead code first (confirmed-zero-import modules, classes, functions)
- Simplify the scheduler pattern: replace trivial dispatchers, add `ctx.next()` enforcement, add pattern tests
- Harden `CommandExecutor`: add configurable timeout and pre-flight disk space check
- Fix `TaskManager` KeyboardInterrupt handler to clean up properly
- Make `DatabaseEngine` injectable for testability
- Delete `_media.py` and consolidate state validation
- Fix layer violations (`utils/db/_sqlalchemy.py`, `utils/progress.py` already documented as known violation)
- Extract video-specific metadata from BaseMedia into Video with `NotImplementedError` stubs in base
- Break up `Video.combine()` into focused strategy classes with zero external API change
- Unify FFmpeg command building pattern across Video and Audio
- Extract 300+ extension mapping from `utils/media.py` to external JSON data file
- All changes preserve backward compatibility — no public API breaks

**Non-Goals:**
- Adding new features beyond the refactoring scope
- Cross-platform support changes (Linux/Windows)
- Rewriting the middleware scheduler pattern from scratch — just simplify and enforce
- Full migration to a different ORM — just clean up the stalled dual-model state
- Performance optimization beyond what falls out of the structural changes

## Decisions

### Decision 1: Dead code deletions are per-file, not monolithic

**Rationale**: Deleting in bulk risks missing an import chain. Per-file approach with pre-deletion grep verification ensures zero false positives. Each file gets: `grep -r 'module_name\|ClassName' src/ base/ utils/ folder.py cli` → confirm zero hits → delete → `lsp_diagnostics` on dependent files.

5 files to delete: `handler.py`, `baidu_translate.py`, `speech.py`, `metaclass.py` — plus selective function removal from `decorator.py`, `tools.py`, `file.py`.

### Decision 2: Scheduler simplification replaces identity-core schedulers, not the pattern

**Rationale**: The MiddlewareScheduler pattern IS valuable for the 2 non-trivial schedulers (`compress`, `scale`). The 4 trivial ones (`convert`, `trim`, `combine`, `media`) are `[middleware, identity_core]` — just function calls. Replacing them in `src/schedulers/folder.py` removes 4 unnecessary closure allocations. The `ctx.next()` enforcement adds a boolean flag on `Context` — minimal change, maximum safety.

### Decision 3: CommandExecutor timeout uses `communicate(timeout=N)` not `Popen` wrapper

**Rationale**: `subprocess.Popen.communicate()` natively supports timeout since Python 3.3+. On timeout, it raises `TimeoutExpired` and the Popen instance's `kill()` can terminate. This is simpler than a wrapper thread or signal-based approach. The timeout value defaults to `None` (no timeout) to preserve backward compatibility.

### Decision 4: DatabaseEngine uses parameter injection, not setter

**Rationale**: A `set_engine()` setter allows mid-execution replacement which can cause race conditions. Instead, `get_engine()` accepts an optional `engine` parameter. When provided, returns it directly (bypassing singleton cache). When None, uses the cached singleton. Tests inject mock engines via parameter. Zero production code changes.

### Decision 5: _media.py deletion requires 3-step verification

**Rationale**: Deletion is irreversible. Three checks before delete:
1. `grep -r '_media' src/ base/ utils/ folder.py cli` — zero hits outside tests
2. Check `src/models/__init__.py` for re-exports that reference `_media`
3. Run full test suite without `_media.py` to catch hidden imports
After deletion, move `_media.py`'s `@validates` state logic into `media.py`'s `update_state()`.

### Decision 6: Video.combine() decomposed by concern, not by helper extraction

**Rationale**: `combine()` handles 5 independent concerns (watermark, audio layering, crop, reverse, color metadata). Extracting each into a strategy class with a common `apply(cmd_list, params) -> None` interface makes the main method a linear pipeline. Each strategy is independently testable. The original `combine()` method stays as the public API — internal implementation only.

### Decision 7: Media extension mapping uses JSON with dict fallback

**Rationale**: JSON is human-readable, diffable, and doesn't require a parser change. The loader reads `media_types.json` at module import time. If the file is missing (installation issue), falls back to the existing hardcoded dict. This provides zero-risk deployment: if the file doesn't exist, behavior is identical to before.

## Risks / Trade-offs

- [Risk] `_media.py` deletion could break a test that imports it → Mitigation: 3-step verification before delete. If tests use it, update imports to `media.py`.
- [Risk] `ctx.next()` enforcement could catch a real use case where middleware intentionally skips core → Mitigation: Audit all existing middleware chains first. If any intentionally skip, the enforcement can be a warning until verified.
- [Risk] `Video.combine()` refactoring could introduce a regression in complex multi-step combine → Mitigation: Existing tests should cover the combine path. Run tests before/after. Add edge case tests if gaps found.
- [Risk] `dead-code-sanitization` capability is spread across 5 files → Mitigation: Each deletion is independent and verified. If any deletion breaks something, only that file needs reverting.
- [Trade-off] `DatabaseEngine` injectability adds a parameter to a frequently-called `get_engine()` → This is a minor API change, but all callers already exist in controlled code. No external consumers.

## Migration Plan

Each refactoring area is independent and can be deployed incrementally:

1. **Phase 1** (risk: none): Dead code deletion + `BoundedExecutor` removal
2. **Phase 2** (risk: low): Scheduler simplification + executor hardening
3. **Phase 3** (risk: low): DatabaseEngine injection + layer violation fixes
4. **Phase 4** (risk: medium): `_media.py` deletion + state consolidation
5. **Phase 5** (risk: medium): `Video.combine()` decomposition + command builder unification
6. **Phase 6** (risk: low-medium): BaseMedia metadata extraction + stubs
7. **Phase 7** (risk: low): Media extension mapping externalization

No rollback needed — each phase preserves backward compatibility. If a phase introduces issues, only that phase's changes need reverting.

## Open Questions

- `utils/progress.py`'s layer violation (`from src.models import *`) is a known documented anti-pattern. Should this refactor include fixing it, or leave it as documented?
- `BoundedExecutor` is unused in production code. Should it stay for reference, or is dead code deletion the intent?
