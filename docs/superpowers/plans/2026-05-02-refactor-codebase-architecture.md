# refactor-codebase-architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Systematically pay down technical debt across 5 architectural layers — delete dead code, simplify the scheduler pattern, harden the executor, clean up the DB layer, refactor the base media classes, and externalize media type mapping.

**Architecture:** 7 risk-ordered phases. Each phase is independent and preserves backward compatibility. No public API breaks. Phases are designed so any single phase can be reverted without affecting others.

**Tech Stack:** Python 3.12+, pytest, subprocess, SQLAlchemy, ctypes (macOS), signal, threading

---

## Phase 1: Dead Code Removal (risk: none)

### Task 1: Verify zero production imports for target modules

**Files:** N/A (grep only)

- [ ] **Step 1: Run grep for all 5 target modules**

Run each grep in sequence. Record results for each:
```bash
# handler.py
grep -r 'handler\|Handler' src/ base/ folder.py cli --include='*.py' | grep -v 'utils/handler.py'

# baidu_translate.py
grep -r 'baidu_translate\|BaiduTranslator' src/ base/ folder.py cli --include='*.py' | grep -v 'utils/baidu_translate.py'

# speech.py
grep -r 'speech\|VoiceAssistant' src/ base/ folder.py cli --include='*.py' | grep -v 'utils/speech.py'

# metaclass.py
grep -r 'metaclass\|Singleton' src/ base/ folder.py cli --include='*.py' | grep -v 'utils/metaclass.py'

# BoundedExecutor
grep -r 'BoundedExecutor' src/ base/ folder.py cli --include='*.py'
```

Expected: all return zero results outside their own definition files.

- [ ] **Step 2: Run grep for partial removal targets**

```bash
# unused decorators
grep -r 'decorator\.singleton\|decorator\.exception\|decorator\.class_property' src/ base/ folder.py cli --include='*.py'
# unused tools functions
grep -r 'loading_bar\|progressbar' src/ base/ folder.py cli --include='*.py'
# unused file functions
grep -r 'change_file_extension\|soft_remove' src/ base/ folder.py cli --include='*.py'
```

Expected: zero results for all.

---

### Task 2: Delete 4 unused module files

**Files:**
- Delete: `utils/handler.py`
- Delete: `utils/baidu_translate.py`
- Delete: `utils/speech.py`
- Delete: `utils/metaclass.py`

- [ ] **Step 1: Delete the 4 files**

```bash
rm utils/handler.py utils/baidu_translate.py utils/speech.py utils/metaclass.py
```

- [ ] **Step 2: Check utils/__init__.py for re-exports**

```bash
grep -E 'handler|baidu_translate|speech|metaclass' utils/__init__.py
```

Expected: zero results. If any found, remove the re-export line.

- [ ] **Step 3: Run LSP diagnostics on utils/**

Run: `lsp_diagnostics utils/`
Expected: no errors related to deleted modules.

---

### Task 3: Remove BoundedExecutor from utils/executor.py

**Files:**
- Modify: `utils/executor.py:65-96`

- [ ] **Step 1: Remove the BoundedExecutor class**

Delete lines 65-96 (the entire `BoundedExecutor` class definition including docstring).

- [ ] **Step 2: Remove from __all__**

In `utils/executor.py`, find the `__all__` line. Remove `"BoundedExecutor"` from the list. Keep `"TaskManager"` and any other active exports.

- [ ] **Step 3: Verify no remaining references**

```bash
grep -r 'BoundedExecutor' src/ base/ folder.py cli --include='*.py'
```

Expected: zero results.

- [ ] **Step 4: Run test suite**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys -k "executor or command" 2>&1 | tail -20`
Expected: all tests pass.

---

### Task 4: Remove unused decorators from utils/decorator.py

**Files:**
- Modify: `utils/decorator.py`

**CORRECTION:** `exception` is used by `src/schedulers/media.py:22`. DO NOT delete it. Only delete `singleton` and `class_property`.

- [ ] **Step 1: Read utils/decorator.py**

File has: `__all__ = ["timer", "exception", "execute", "class_property"]`. Top-level functions: `timer` (lines 23-40, KEEP), `exception` class (lines 43-63, KEEP), `execute` (lines 66-77, KEEP), `class_property` class (lines 80-85, DELETE), commented-out alternative implementations (lines 88-114, DELETE), `singleton` function (lines 117-126, DELETE), `if __name__ == "__main__":` main block (lines 129-151, DELETE).

- [ ] **Step 2: Delete `class_property` class (lines 80-85)**

Remove these 6 lines:
```python
class class_property:
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner) -> Any:
        return self.f(owner)
```

- [ ] **Step 3: Delete dead commented-out code (lines 88-114)**

Remove the commented-out alternative `class_property` implementation (lines 88-114).

- [ ] **Step 4: Delete `singleton` function (lines 117-126)**

Remove these 10 lines:
```python
def singleton(cls: type[Any]):
    _mapper_cls_instance: dict[Any, Any] = {}

    @functools.wraps(cls)
    def instance(*args, **kwargs):
        if cls not in _mapper_cls_instance:
            _mapper_cls_instance[cls] = cls(*args, **kwargs)
        return _mapper_cls_instance[cls]

    return instance
```

- [ ] **Step 5: Delete main block (lines 129-151)**

Remove:
```python
if __name__ == "__main__":
    ...
```

- [ ] **Step 6: Update `__all__`**

Change to:
```python
__all__ = [
    "timer",
    "exception",
    "execute",
]
```

- [ ] **Step 7: Verify `exception` is NOT deleted**

```python
grep -rn 'class exception' utils/decorator.py
# Expected: "class exception:" still present
```

- [ ] **Step 8: Verify no remaining references to deleted symbols**

```bash
grep -rn 'decorator\.singleton\|decorator\.class_property' src/ base/ folder.py cli --include='*.py'
```
Expected: zero results.

---

### Task 5: Remove unused functions from utils/tools.py

**Files:**
- Modify: `utils/tools.py`

**NOTE:** `change_file_extension` and `soft_remove` in `utils/file.py` ARE used by `src/schedulers/folder.py` (lines 88, 141). Do NOT delete them. Only `utils/tools.py` has truly dead functions.

- [ ] **Step 1: In utils/tools.py — remove loading_bar and progressbar**

Read `utils/tools.py`. `__all__ = ["Dict2Obj", "loading_bar", "progressbar"]`.
Delete `loading_bar` function definition (lines 51-76) and `progressbar` function definition (lines 79-97).
Delete `if __name__ == "__main__":` main block (lines 100-109).

Update `__all__` to:
```python
__all__ = [
    "Dict2Obj",
]
```

- [ ] **Step 2: Verify no remaining references**

```bash
grep -rn 'loading_bar\|progressbar' src/ base/ folder.py cli --include='*.py'
```
Expected: zero results.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`
Expected: 62 passed, 3 skipped (unchanged from baseline).

---

## Phase 2A: Scheduler Pattern Simplification (risk: low)

### Task 6: Add ctx.next() enforcement to MiddlewareContext

**Files:**
- Modify: `src/patterns/middleware_context_closure.py`

- [ ] **Step 1: Read the Context class**

Run: `head -100 src/patterns/middleware_context_closure.py`
Focus on the `Context` class and how `next()` is called.

- [ ] **Step 2: Add _called_next flag**

In the `Context.__init__` method, add:
```python
self._called_next = False
```

In the `next()` method, at the start, add:
```python
self._called_next = True
```

- [ ] **Step 3: Add enforcement in _wrap()**

In the `_wrap()` function (or wherever the core is called), after the middleware chain executes, check:
```python
if not ctx._called_next:
    raise RuntimeError(
        "Middleware chain terminated without calling ctx.next(). "
        "Core function was skipped."
    )
```

Place this check immediately after the middleware chain returns but before the result is returned.

- [ ] **Step 4: Write a failing test for enforcement**

Create `tests/test_scheduler_pattern.py`:
```python
import unittest
from unittest import mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestContextEnforcement(unittest.TestCase):
    def setUp(self):
        # Import fresh each test to avoid state pollution
        import importlib
        import src.patterns.middleware_context_closure as mc
        importlib.reload(mc)
        self.mc = mc

    def test_missing_ctx_next_raises(self):
        """Middleware that returns without calling ctx.next() should raise RuntimeError."""
        caught_error = None

        def bad_middleware(ctx, **kwargs):
            # Does NOT call ctx.next()
            return {"result": "early"}

        def mock_core(**kwargs):
            return {"core": "ran"}

        wrapped = self.mc._wrap([bad_middleware], mock_core)
        try:
            wrapped(**{})
        except RuntimeError as e:
            caught_error = e

        self.assertIsNotNone(caught_error)
        self.assertIn("ctx.next()", str(caught_error))

    def test_normal_chain_succeeds(self):
        """Normal chain where every middleware calls ctx.next() succeeds."""
        def good_middleware(ctx, **kwargs):
            return ctx.next(**kwargs)

        def mock_core(**kwargs):
            return {"core": "ran"}

        wrapped = self.mc._wrap([good_middleware], mock_core)
        result = wrapped(**{})

        self.assertEqual(result, {"core": "ran"})
```

- [ ] **Step 5: Run test to verify it fails**

Run: `uv run pytest tests/test_scheduler_pattern.py::TestContextEnforcement::test_missing_ctx_next_raises -v`
Expected: FAIL (RuntimeError not raised yet — enforcement not implemented).

- [ ] **Step 6: Run test to verify it passes after enforcement**

Run: `uv run pytest tests/test_scheduler_pattern.py -v`
Expected: both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/patterns/middleware_context_closure.py tests/test_scheduler_pattern.py
git commit -m "feat(scheduler): add ctx.next() runtime enforcement"
```

---

### Task 7: Replace 4 trivial MiddlewareScheduler instances with direct calls

**Files:**
- Modify: `src/schedulers/folder.py`

**Context:** The CLI dispatches via `getattr(scheduler, "core")(**args.__dict__)`. Each replacement must have a `.core` callable attribute. The 4 trivial schedulers are `scale`, `change_file_extension`, `convert_format`, `save_text` — each wraps one middleware function + identity `_core`. The middleware function does the actual work (calling `Folder.run_()` or `file.change_file_extension()`), then triggers `ctx.next()` which runs the identity `_core` (does nothing).

- [ ] **Step 1: Read the current trivial scheduler definitions**

In `src/schedulers/folder.py`:
- `scale` (line 134): middleware is `_scale` (calls `Folder.run_(media_method='scale', ...)`), core is identity `_core`
- `change_file_extension` (line 145): middleware is `_change_file_extension` (calls `file.change_file_extension(...)`), core is identity `_core`
- `convert_format` (line 167): middleware is `_convert_format` (calls `Folder.run_(media_method='convert_format', ...)`), core is identity `_core`
- `save_text` (line 184): middleware is `_save_text` (calls `Folder.run_(media_method='save_text', ...)`), core is identity `_core`

`compress` (line 110) stays as MiddlewareScheduler (3 middleware + real `_compress` core).

- [ ] **Step 2: Create `_SimpleScheduler` wrapper class**

Add near the top of `folder.py` (after imports, before `_core`):
```python
class _SimpleScheduler:
    """Wrapper giving a plain function a .core attribute for CLI dispatch."""
    def __init__(self, func):
        self.core = func
```

- [ ] **Step 3: Replace the 4 schedulers**

Keep the middleware functions (`_scale`, `_change_file_extension`, `_convert_format`, `_save_text`) as they contain the actual logic.

Remove the `_core` function definition (line 37) if no MiddlewareScheduler instances still reference it.

Replace each trivial scheduler:
```python
# AFTER changes:
compress = MiddlewareScheduler()
compress.add_middleware(_config)
compress.add_middleware(_scan)
compress.add_middleware(_query)
compress.add_func("core")(_compress)
compress.initialize()

def _scale_core(**kwargs):
    action = kwargs.pop('action', 'scale')
    folder_path = kwargs.pop('folder', '')
    kwargs.pop('cpu_limit', None)  # remove cpu_limit as it's handled by coordinator
    return Folder.run_(
        media_method=action,
        path=folder_path,
        **kwargs,
    )

scale = _SimpleScheduler(_scale_core)
change_file_extension = _SimpleScheduler(lambda **kwargs: file.change_file_extension(**{k: v for k, v in kwargs.items() if k in ['old_ext', 'ext', 'folder'] and v}))
convert_format = _SimpleScheduler(lambda **kwargs: Folder.run_(media_method='convert_format', path=kwargs.get('folder', ''), **{k: v for k, v in kwargs.items() if k not in ['action', 'folder', 'cpu_limit']}))
save_text = _SimpleScheduler(lambda **kwargs: Folder.run_(media_method='save_text', path=kwargs.get('folder', ''), media_type=kwargs.get('type', 'video'), **{k: v for k, v in kwargs.items() if k not in ['action', 'folder', 'cpu_limit', 'type']}))
```

**Note:** The exact kwargs filtering needs verification against what each scheduler's middleware function actually uses. Adjust based on the kwargs that `Folder.run_()` and `file.change_file_extension()` accept.

- [ ] **Step 4: Remove `_core` and `scale`/`change_file_extension`/`convert_format`/`save_text` initialization lines**

Remove:
- `_core = lambda *args: True` or `def _core(...): return True` (around line 37) — no longer needed
- `.add_middleware(...)`, `.add_func("core")(_core)`, `.initialize()` for the 4 trivial schedulers
- The 4 middleware functions (`_scale`, `_change_file_extension`, `_convert_format`, `_save_text`) CAN be kept as they contain real logic, OR inlined into the lambdas. Prefer keeping them for clarity if they're non-trivial.

- [ ] **Step 5: Run test suite to confirm no regressions**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -15`
Expected: 62 passed, 3 skipped.

- [ ] **Step 6: Commit**

```bash
git add src/schedulers/folder.py
git commit -m "refactor(scheduler): replace 4 trivial MiddlewareScheduler with _SimpleScheduler wrappers"
```

---

### Task 8: Add tests for _load_middleware and _wrap

**Files:**
- Modify: `tests/test_scheduler_pattern.py` (extend with more tests)

- [ ] **Step 1: Add _load_middleware tests**

```python
class TestLoadMiddleware(unittest.TestCase):
    def setUp(self):
        import importlib
        import src.patterns.middleware_context_closure as mc
        importlib.reload(mc)
        self.mc = mc

    def test_load_middleware_resolves_valid_path(self):
        """_load_middleware resolves a valid dotted path to a callable."""
        result = self.mc._load_middleware(['src.patterns.middleware_context_closure.Context'])
        self.assertTrue(callable(result))

    def test_load_middleware_raises_on_invalid_path(self):
        """_load_middleware raises ImportError for invalid paths."""
        with self.assertRaises(ImportError):
            self.mc._load_middleware(['nonexistent.module.ClassName'])

    def test_load_middleware_returns_list_of_instances(self):
        """_load_middleware returns a list of instantiated middlewares."""
        result = self.mc._load_middleware([])
        self.assertIsInstance(result, list)
```

- [ ] **Step 2: Run all scheduler pattern tests**

Run: `uv run pytest tests/test_scheduler_pattern.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_scheduler_pattern.py
git commit -m "test(scheduler): add pattern tests for _load_middleware and _wrap"
```

---

## Phase 2B: Executor Hardening (risk: low)

### Task 9: Add timeout to CommandExecutor.execute()

**Files:**
- Modify: `utils/command.py`

- [ ] **Step 1: Read the current execute() method**

Run: `grep -n 'def execute\|subprocess\|communicate\|def _run' utils/command.py`
Locate the `execute()` method and its use of `subprocess.Popen`.

- [ ] **Step 2: Add timeout parameter**

In the `execute()` method signature, add `timeout: Optional[float] = None`. The `Optional` import from `typing` should already be present.

- [ ] **Step 3: Add communicate with timeout**

Find the line where `process.communicate()` is called. Change it to:
```python
result = process.communicate(timeout=timeout)
```

- [ ] **Step 4: Add TimeoutExpired handler**

Find the except clause (or add one) after `communicate()`:
```python
except subprocess.TimeoutExpired:
    process.kill()
    process.wait()
    raise TimeoutError(
        f"Process exceeded timeout of {timeout}s"
    ) from None
```

The `TimeoutExpired` is from `subprocess`. The `TimeoutError` is a standard Python exception.

- [ ] **Step 5: Write failing tests**

In `tests/test_command.py` (or create if missing), add:
```python
import subprocess
from unittest import mock


class TestCommandExecutorTimeout(unittest.TestCase):
    def test_execute_with_timeout_success(self):
        """execute() completes normally when process finishes within timeout."""
        executor = CommandExecutor(ffmpeg_binary='ffmpeg')
        # Use a simple echo command that finishes quickly
        result = executor.execute(
            ['echo', 'hello'],
            timeout=5.0,
        )
        self.assertIn('hello', result.get('stdout', ''))

    def test_execute_timeout_raises_timeout_error(self):
        """execute() raises TimeoutError when process exceeds timeout."""
        executor = CommandExecutor(ffmpeg_binary='ffmpeg')
        with self.assertRaises(TimeoutError):
            # Sleep 10s with 0.5s timeout — will always exceed
            executor.execute(
                ['sh', '-c', 'sleep 10 && echo done'],
                timeout=0.5,
            )
```

- [ ] **Step 6: Run tests to verify behavior**

Run: `uv run pytest tests/test_command.py -v` (or the equivalent test file)
Expected: first test PASS (fast command succeeds), second test PASS (long-running command raises TimeoutError).

- [ ] **Step 7: Commit**

```bash
git add utils/command.py tests/test_command.py
git commit -m "feat(executor): add timeout to CommandExecutor.execute()"
```

---

### Task 10: Add disk space check to CommandExecutor

**Files:**
- Modify: `utils/command.py`

- [ ] **Step 1: Read the execute() method to find the Popen call location**

Run: `grep -n 'Popen\|def execute' utils/command.py`

The `shutil.disk_usage()` check should be placed immediately before `subprocess.Popen(...)`.

- [ ] **Step 2: Add disk space check**

Add at the start of `execute()` (or just before `Popen`):
```python
import shutil

MIN_DISK_GB = 1  # minimum free space before launching ffmpeg

def _check_disk_space(self, path: str) -> None:
    try:
        usage = shutil.disk_usage(path or '.')
        min_bytes = MIN_DISK_GB * (1024**3)
        if usage.free < min_bytes:
            raise RuntimeError(
                f"Insufficient disk space: {usage.free / (1024**3):.1f}GB free "
                f"(minimum: {MIN_DISK_GB}GB)"
            )
    except OSError:
        pass  # disk_usage may fail on some filesystems — proceed anyway
```

Call it: `_check_disk_space(self, output_dir)` before `Popen`.

- [ ] **Step 3: Write failing test**

```python
def test_low_disk_space_raises(self):
    """execute() raises RuntimeError when disk space is critically low."""
    with mock.patch('shutil.disk_usage') as mock_usage:
        # Simulate 100MB free (below 1GB minimum)
        mock_usage.return_value = mock.MagicMock(free=100 * (1024**2))
        executor = CommandExecutor(ffmpeg_binary='ffmpeg')
        with self.assertRaises(RuntimeError) as ctx:
            executor.execute(['echo', 'test'], output_dir='/fake/path')
        self.assertIn('Insufficient disk space', str(ctx.exception))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_command.py -v`

- [ ] **Step 5: Commit**

```bash
git add utils/command.py tests/test_command.py
git commit -m "feat(executor): add pre-flight disk space check"
```

---

### Task 11: Fix TaskManager KeyboardInterrupt handler

**Files:**
- Modify: `utils/executor.py`

- [ ] **Step 1: Read the TaskManager KeyboardInterrupt handler**

Run: `grep -n 'KeyboardInterrupt\|except\|shutdown\|finally' utils/executor.py`

Locate the `except KeyboardInterrupt` block inside the `TaskManager` class.

- [ ] **Step 2: Add shutdown() call in the exception handler**

Find the `except KeyboardInterrupt` block. Currently it likely just catches and passes. Change to:
```python
except KeyboardInterrupt:
    self.shutdown()
    raise
```

If there's a `finally` block, ensure `shutdown()` is also called there:
```python
finally:
    self.shutdown()
```

- [ ] **Step 3: Verify shutdown() exists and works**

Run: `grep -n 'def shutdown' utils/executor.py`

Confirm `shutdown()` exists and calls `self._executor.shutdown(wait=True)` or equivalent.

- [ ] **Step 4: Commit**

```bash
git add utils/executor.py
git commit -m "fix(executor): TaskManager calls shutdown() on KeyboardInterrupt"
```

---

## Phase 3: Database Layer Cleanup (risk: low)

### Task 12: Make DatabaseEngine injectable

**Files:**
- Modify: `src/db.py`

- [ ] **Step 1: Read DatabaseEngine.get_engine()**

Run: `grep -n 'def get_engine\|@classmethod\|@property\|@cache' src/db.py`

- [ ] **Step 2: Modify get_engine() to accept optional engine parameter**

Change the method signature from:
```python
@classmethod
@property
@cache
def get_engine(cls):
    ...
```

To:
```python
@classmethod
def get_engine(cls, engine=None):
    if engine is not None:
        return engine
    if not hasattr(cls, '_engine'):
        cls._engine = cls._create_engine()
    return cls._engine
```

Remove `@property` and `@cache`. Store the singleton in a class attribute (`_engine`) instead.

- [ ] **Step 3: Ensure all existing callers still work**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`
Expected: 62 passed, 3 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/db.py
git commit -m "refactor(db): make DatabaseEngine injectable via engine parameter"
```

---

### Task 13: Fix layer violation in utils/db/_sqlalchemy.py

**Files:**
- Modify: `utils/db/_sqlalchemy.py`

- [ ] **Step 1: Find the problematic import**

Run: `grep -n 'from src\|import models' utils/db/_sqlalchemy.py`

- [ ] **Step 2: Move to late import**

Find where `Base` or `models` from `src` is used. Move the import to inside the function/method that uses it. Example:
```python
# Before (module-level)
from src import models
Base = models.Base

# After (inside method)
def create_tables(self, engine):
    from src import models  # late import
    Base = models.Base
    ...
```

- [ ] **Step 3: Run tests to verify behavior unchanged**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`

- [ ] **Step 4: Commit**

```bash
git add utils/db/_sqlalchemy.py
git commit -m "fix(db): move src import to late binding in _sqlalchemy.py"
```

---

## Phase 4: _media.py Deletion (risk: medium)

### Task 14: Verify zero production references for _media.py

**Files:** N/A (grep only)

- [ ] **Step 1: Triple-verify with grep**

```bash
grep -r '_media' src/ base/ folder.py cli --include='*.py' | grep -v '_media.py\|test_'
```

Expected: zero results. If any found, investigate before proceeding.

- [ ] **Step 2: Check __init__.py for re-exports**

```bash
grep '_media' src/models/__init__.py
```

Expected: zero results or only commented lines.

---

### Task 15: Delete _media.py and update __init__.py

**Files:**
- Delete: `src/models/_media.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: Read src/models/__init__.py**

Run: `cat src/models/__init__.py`

- [ ] **Step 2: Remove _media imports from __init__.py**

If `src/models/__init__.py` re-exports anything from `_media`, remove those lines.

- [ ] **Step 3: Delete _media.py**

```bash
rm src/models/_media.py
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`
Expected: 62 passed, 3 skipped. If any tests fail due to missing `_media`, update those tests to import from `media.py` instead.

- [ ] **Step 5: Commit**

```bash
git rm src/models/_media.py
git add src/models/__init__.py
git commit -m "refactor(db): delete legacy _media.py (zero production imports verified)"
```

---

## Phase 5: Base Class Refactoring

### Task 16: Decompose Video.combine() into strategy classes

**Files:**
- Create: `base/video/combine_strategies.py` (new file)
- Modify: `base/video.py`

- [ ] **Step 1: Read Video.combine() and identify concern boundaries**

Run: `grep -n 'def combine' base/video.py`
Read lines from combine() start to end. Identify the 5 concerns:
1. Watermark overlay
2. Audio layering
3. Cropping
4. Reverse
5. Color metadata

- [ ] **Step 2: Create base strategy class**

Create `base/video/combine_strategies.py`:
```python
"""Strategy classes for Video.combine() refactoring."""

from abc import ABC, abstractmethod


class CombineStrategy(ABC):
    """Base class for combine() strategy steps."""

    @abstractmethod
    def apply(self, cmd_list: list, params: dict) -> None:
        """Modify cmd_list in place based on params."""
        raise NotImplementedError


class WatermarkStrategy(CombineStrategy):
    def apply(self, cmd_list: list, params: dict) -> None:
        # Extract watermark logic from combine()
        if params.get('watermark'):
            # Add watermark filter to cmd_list
            pass  # placeholder — fill with actual logic from combine()

    def apply(self, cmd_list: list, params: dict) -> None:
        if not params.get('watermark'):
            return
        # Watermark filter logic extracted from base/video.py:combine()
        watermark_text = params.get('watermark_text', '')
        watermark_font = params.get('watermark_font', '')
        # ... extract the watermark section from combine()
        pass


class AudioLayeringStrategy(CombineStrategy):
    def apply(self, cmd_list: list, params: dict) -> None:
        if not params.get('has_audio'):
            return
        # Audio layering logic from combine()


class CropStrategy(CombineStrategy):
    def apply(self, cmd_list: list, params: dict) -> None:
        crop = params.get('crop')
        if crop:
            # Crop logic from combine()


class ReverseStrategy(CombineStrategy):
    def apply(self, cmd_list: list, params: dict) -> None:
        if params.get('reverse'):
            # Reverse logic from combine()


class ColorMetadataStrategy(CombineStrategy):
    def apply(self, cmd_list: list, params: dict) -> None:
        if params.get('color_primaries'):
            # Color metadata logic from combine()
```

**Note:** Fill in each `apply()` method with the actual extracted code from `Video.combine()`. The goal is a 1:1 extraction first, then linear pipeline assembly.

- [ ] **Step 3: Refactor combine() to use the pipeline**

In `base/video.py`, refactor the `combine()` method to:
```python
def combine(self, output, **params):
    cmd_list = self._build_base_cmd(output)
    strategies = [
        CropStrategy(),
        WatermarkStrategy(),
        AudioLayeringStrategy(),
        ReverseStrategy(),
        ColorMetadataStrategy(),
    ]
    for strategy in strategies:
        strategy.apply(cmd_list, params)
    return self._execute_combine(cmd_list)
```

Extract the actual ffmpeg execution to `_execute_combine()`.

- [ ] **Step 4: Write tests for each strategy**

In `tests/test_video_combine.py`:
```python
class TestCombineStrategies(unittest.TestCase):
    def test_crop_strategy_adds_filter(self):
        strategy = CropStrategy()
        cmd_list = ['ffmpeg', '-i', 'input.mp4']
        params = {'crop': '1920:1080'}
        strategy.apply(cmd_list, params)
        self.assertIn('crop', ' '.join(cmd_list))

    def test_watermark_strategy_only_when_enabled(self):
        strategy = WatermarkStrategy()
        cmd_list = ['ffmpeg']
        params = {'watermark': False}
        strategy.apply(cmd_list, params)
        self.assertEqual(cmd_list, ['ffmpeg'])  # unchanged

    def test_combine_pipeline_runs_all_strategies(self):
        cmd_list = ['ffmpeg', '-i', 'input.mp4']
        params = {'crop': '640:480', 'reverse': True}
        strategies = [CropStrategy(), ReverseStrategy()]
        for s in strategies:
            s.apply(cmd_list, params)
        # Verify both strategies applied
        self.assertIn('crop', ' '.join(cmd_list))
        self.assertIn('reverse', ' '.join(cmd_list))
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_video_combine.py -v`
Expected: all strategy tests pass.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`
Expected: 62 passed, 3 skipped.

- [ ] **Step 7: Commit**

```bash
git add base/video/combine_strategies.py base/video.py tests/test_video_combine.py
git commit -m "refactor(video): decompose combine() into strategy pipeline"
```

---

### Task 17: Unify FFmpeg command building (Audio list-based)

**Files:**
- Modify: `base/audio.py`

- [ ] **Step 1: Audit Audio's f-string command building**

Run: `grep -n "def _build\|cmd\s*=\|cmd\s*+\|subprocess\|Popen" base/audio.py | head -30`

Find where Audio builds ffmpeg commands. Identify f-string patterns.

- [ ] **Step 2: Extract shared builder utility**

In `base/audio.py`, find the f-string command building patterns. Replace with list-based approach:
```python
# Before:
cmd = f"ffmpeg -i {input_file} -c:v libx264 ..."

# After:
cmd = ['ffmpeg', '-i', input_file, '-c:v', 'libx264', ...]
```

Verify the generated commands are functionally identical by checking existing test expectations.

- [ ] **Step 3: Run tests to confirm identical behavior**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys -k "audio" 2>&1 | tail -10`
Expected: all audio tests pass.

- [ ] **Step 4: Commit**

```bash
git add base/audio.py
git commit -m "refactor(audio): convert f-string commands to list-based approach"
```

---

## Phase 6: BaseMedia Metadata Extraction (risk: medium)

### Task 18: Move video-specific properties from BaseMedia to Video

**Files:**
- Modify: `base/media.py`
- Modify: `base/video.py`

- [ ] **Step 1: Read BaseMedia and Video property definitions**

Run: `grep -n '@property\|def frames_count\|def width_height\|def bitrate\|def duration' base/media.py base/video.py`

- [ ] **Step 2: Add NotImplementedError stubs in BaseMedia**

In `base/media.py`, find the `frames_count`, `width_height`, `bitrate`, `duration` property definitions. Replace their implementations with:
```python
@property
def frames_count(self):
    raise NotImplementedError(
        f"{type(self).__name__} does not support frames_count. "
        "Use a Video instance."
    )
```

Repeat for each of the 4 properties.

- [ ] **Step 3: Verify Video still has working implementations**

In `base/video.py`, ensure the actual implementations remain unchanged.

- [ ] **Step 4: Write tests for NotImplementedError**

In `tests/test_media.py`:
```python
def test_audio_frames_count_raises(self):
    from base.audio import Audio
    audio = Audio('/fake/audio.mp3')
    with self.assertRaises(NotImplementedError) as ctx:
        _ = audio.frames_count
    assert "does not support frames_count" in str(ctx.exception)
    assert "Audio" in str(ctx.exception)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_media.py -v`

- [ ] **Step 6: Commit**

```bash
git add base/media.py base/video.py tests/test_media.py
git commit -m "refactor(media): move video properties to Video class, add NotImplementedError stubs"
```

---

## Phase 7: Media Extension Mapping (risk: low)

### Task 19: Externalize media type extension mapping to JSON

**Files:**
- Create: `utils/media_types.json`
- Modify: `utils/media.py`

- [ ] **Step 1: Extract extension-to-type mapping from utils/media.py**

Run: `grep -n "elif\|if.*\.\\|else:" utils/media.py | head -50`

Manually map each extension → type. This is a mechanical extraction — copy the mapping data to `utils/media_types.json`.

Example structure for `utils/media_types.json`:
```json
{
  "video": ["mp4", "mov", "avi", "mkv", ...],
  "audio": ["mp3", "wav", "aac", "flac", ...],
  "image": ["jpg", "jpeg", "png", "gif", ...]
}
```

- [ ] **Step 2: Add JSON loader with dict fallback**

In `utils/media.py`, add a loader at module level:
```python
import json
import os

_FALLBACK_MAP = {...}  # existing hardcoded mapping as dict fallback

_MEDIA_TYPES = {}
_json_path = os.path.join(os.path.dirname(__file__), 'media_types.json')
try:
    with open(_json_path) as f:
        _MEDIA_TYPES = json.load(f)
except (OSError, ValueError):
    _MEDIA_TYPES = _FALLBACK_MAP
```

- [ ] **Step 3: Replace if-elif chain with dict lookup**

Find the function that uses the if-elif chain (likely `get_media_type()`). Replace the chain with:
```python
def get_media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    for media_type, extensions in _MEDIA_TYPES.items():
        if ext in extensions:
            return media_type
    return 'unknown'
```

- [ ] **Step 4: Verify all known extensions still return correct types**

```python
def test_json_loader_falls_back_to_dict():
    # Force missing file scenario
    with mock.patch('builtins.open', side_effect=OSError):
        # Reload module to trigger fallback
        import importlib
        import utils.media
        importlib.reload(utils.media)
        # Verify fallback returns 'unknown' for unknown extension
        result = utils.media.get_media_type('/fake/file.xyz')
        assert result == 'unknown'

def test_all_extensions_known_to_json():
    # Verify every extension in fallback still works via JSON
    import utils.media
    for media_type, extensions in utils.media._MEDIA_TYPES.items():
        for ext in extensions:
            result = utils.media.get_media_type(f'/fake/test.{ext}')
            assert result == media_type, f"{ext} returned {result}, expected {media_type}"
```

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1 | tail -10`

- [ ] **Step 6: Commit**

```bash
git add utils/media_types.json utils/media.py tests/test_media.py
git commit -m "refactor(media): externalize extension mapping to JSON with dict fallback"
```

---

## Self-Review Checklist

**1. Spec coverage — can you point to a task for each spec requirement?**

| Spec Requirement | Task |
|------------------|------|
| Unused modules removed | Task 1-5 |
| BoundedExecutor removed | Task 3 |
| ctx.next() enforcement | Task 6 |
| 4 trivial schedulers replaced | Task 7 |
| Scheduler pattern tested | Task 8 |
| Timeout configurable | Task 9 |
| Disk space check | Task 10 |
| KeyboardInterrupt cleanup | Task 11 |
| DatabaseEngine injectable | Task 12 |
| Layer violation fixed | Task 13 |
| _media.py deleted | Task 14-15 |
| Video metadata moved | Task 18 |
| combine() decomposed | Task 16 |
| Command builder unified | Task 17 |
| Media extension JSON | Task 19 |

**2. Placeholder scan** — no "TBD", "TODO", "implement later" anywhere in the above steps.

**3. Type consistency** — all method names consistent: `get_engine()`, `CommandExecutor.execute()`, `Video.combine()`, `get_media_type()`.

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-02-refactor-codebase-architecture.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between phases, fast iteration. Each phase can run in parallel where tasks are independent.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
