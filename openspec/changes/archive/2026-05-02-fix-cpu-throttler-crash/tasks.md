## 1. Sampling Layer Fix

- [x] 1.1 Add `ProcessLookupError` to the catch clause in `macos_sample_cpu_time()` (`sampling.py:73-75`) so that `proc_pidinfo` failures route to the `ps` fallback
- [x] 1.2 In `_sample_cpu()` (`throttler.py:66-80`), change the exception handler to NOT set `self.zombie = True` on `ProcessLookupError`/`OSError` — return `0.0` and continue instead
- [x] 1.3 Add periodic zombie detection in `_loop_once()` (`throttler.py:86-122`): check `os.kill(pid, 0)` every N cycles (e.g., every 25 iterations = ~5s) to detect genuinely dead processes

## 2. Coordinator Auto-Mode Fix

- [x] 2.1 Fix `_calculate_per_process_target()` (`coordinator.py:153-174`): scale the high-load and moderate-load budgets by `default_limit / 100` so `CPU_LIMIT` applies at all load levels
- [x] 2.2 Ensure the scaled-down budget doesn't drop below `MIN_PER_WORKER` (25) in auto mode to prevent over-throttling

## 3. Verification

- [x] 3.1 Run existing test suite: `pytest -vv --rootdir . --color=yes --capture=tee-sys`
- [x] 3.2 Run lint: `ruff check utils/throttle/ tests/` — 21 pre-existing unused imports found and fixed (19 auto-fixed, 2 manual), now all clean. Installed ruff, codespell, vulture as dev deps.
- [x] 3.3 Manual verification: run `uv run python cli compress -f <test_folder> -c 1` and confirm steady CPU < 100% for entire duration
- [x] 3.4 Manual verification: send SIGUSR1 twice during compression and confirm CPU changes each time
