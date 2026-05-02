## Why

The CPU throttler (`ProcessThrottler`) crashes on its first SIGSTOP cycle during ffmpeg execution on macOS. After the crash, the ffmpeg process runs completely unthrottled at ~450% CPU. Subsequent SIGUSR1 signals update the coordinator state but have no effect — no active throttlers exist. This makes all CPU throttling features (`CPU_LIMIT` env var, `-c` CLI flag, SIGUSR1 dynamic profile cycling) effectively single-use and unreliable.

Additionally, `CPU_LIMIT` in auto mode is ignored whenever system load exceeds 50% — the budget is hardcoded to 25 or 50 regardless of the configured limit.

## What Changes

- **Fix throttler crash on SIGSTOP'd processes**: `proc_pidinfo()` on macOS can fail for SIGSTOP'd processes. When `_sample_cpu()` catches `ProcessLookupError`, it sets `zombie=True` which permanently kills the throttler thread. This must be handled gracefully — a single failed sample should not destroy the throttler.
- **Add throttler self-recovery**: If the throttler detects a persistent sampling failure, it should retry rather than permanently die.
- **Fix `CPU_LIMIT` env var behavior in auto mode**: The current logic bypasses `default_limit` under moderate/high system load (>50%). The `CPU_LIMIT` value should be applied as a ceiling across all load conditions.
- **Improve error logging**: Add context to throttler crash logs so future debugging is faster.

## Capabilities

### New Capabilities
- `cpu-throttler`: CPU throttling system for external subprocesses (ffmpeg). Covers sampling, duty-cycle control (SIGSTOP/SIGCONT), coordinator state management, and signal-based profile cycling.

### Modified Capabilities
*(none)*

## Impact

- `utils/throttle/sampling.py` — catch `ProcessLookupError` in `macos_sample_cpu_time()`, don't propagate to caller
- `utils/throttle/throttler.py` — handle sampling failures gracefully in `_sample_cpu()`, add throttler health monitoring
- `utils/throttle/coordinator.py` — fix auto-mode target calculation to respect `default_limit` under all load conditions
