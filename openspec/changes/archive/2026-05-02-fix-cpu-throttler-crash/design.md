## Context

The CPU throttling system uses a coordinator → throttler → sampler architecture:

```
CPULimiterCoordinator (coordinator.py)
  └── ProcessThrottler (throttler.py, 1 per PID)
        └── _sample_cpu() → sample_cpu_time() → macos_sample_cpu_time()
              └── _macos_proc_pidinfo() via ctypes OR _macos_ps_fallback()
```

On macOS, `_macos_proc_pidinfo()` uses `proc_pidinfo(PROC_PIDTASKINFO)` via ctypes to read CPU time. This call can fail when the target process is in SIGSTOP state (behavior varies by macOS version). When it fails, `ProcessLookupError` propagates to `_sample_cpu()`, which marks the throttler as zombie — permanently killing the thread.

The `finally` block sends SIGCONT, the process resumes unthrottled, and subsequent SIGUSR1 signals update only the coordinator state (no active throttlers to receive profile changes).

Additionally, `_calculate_per_process_target()` in auto mode has three branches:
- load > 80% → total_budget = 25 (CPU_LIMIT ignored)
- load 50-80% → total_budget = 50 (CPU_LIMIT ignored)
- load < 50% → total_budget = 100 * (CPU_LIMIT / 100)

This means `CPU_LIMIT=1` has no effect whenever system load exceeds 50% (which is essentially always during ffmpeg compress at 450% CPU).

## Goals / Non-Goals

**Goals:**
- The throttler survives the entire duration of the ffmpeg subprocess without crashing
- `CPU_LIMIT` env var and `-c` CLI flag reliably cap CPU usage at the configured value
- SIGUSR1 profile cycling works reliably (multiple signals across throttler lifetime)
- Failed CPU samples are handled gracefully (log + retry, not kill the throttler)

**Non-Goals:**
- Cross-platform throttling (Linux/Windows support is out of scope)
- Improving throttling precision (current ~1s window with 0.2s sampling is acceptable)
- Refactoring the middleware scheduler pattern or coordinator architecture
- Adding new SIGUSR1 profiles beyond the existing [None, 100, 50, 25] cycle

## Decisions

### Decision 1: Catch ProcessLookupError in sampling layer, not throttler layer

**Rationale**: The crash happens because `ProcessLookupError` from `_macos_proc_pidinfo()` bypasses the `macos_sample_cpu_time()` catch clause (which only catches `ImportError`, `AttributeError`, `OSError`) and propagates to `_sample_cpu()` where it triggers zombie mode.

**Approach**: Add `ProcessLookupError` to the catch clause in `macos_sample_cpu_time()`, routing to the `ps` fallback. If `ps` also fails, return `0.0` and log a warning.

**Why not fix it in `_sample_cpu()`**: The zombie mechanism exists to handle the case where the process has genuinely exited. We don't want to remove zombie detection entirely — we just want to distinguish "process is gone" from "sampling failed temporarily."

### Decision 2: Change `_sample_cpu()` to not set zombie on single failure

**Rationale**: A single `proc_pidinfo` failure does not mean the process died. It could be a transient state (SIGSTOP interference, macOS security policy). Setting `zombie=True` permanently kills the throttler, which is unrecoverable.

**Approach**: Replace the `(ProcessLookupError, OSError)` handler in `_sample_cpu()` to return `0.0` without setting zombie. Move zombie detection to a separate mechanism: check `os.kill(pid, 0)` periodically (separate from sampling) to detect genuinely dead processes.

### Decision 3: Fix auto-mode target calculation to respect CPU_LIMIT

**Rationale**: `CPU_LIMIT` is user-configured and should act as a ceiling, not merely a low-load optimization.

**Approach**: Change the auto-mode calculation so `CPU_LIMIT` scales the budget proportionally:

| Load | Current behavior | New behavior |
|------|-----------------|--------------|
| >80% | total=25 | total = 25 * (CPU_LIMIT/100) |
| 50-80% | total=50 | total = 50 * (CPU_LIMIT/100) |
| <50% | total=CPU_LIMIT | total = CPU_LIMIT (unchanged) |

This makes `CPU_LIMIT=1` effective at all load levels: at high load, total ≈ 25 * 0.01 = 0.25, clamped to MIN_PER_WORKER (25). Result: per_worker ≈ 25% per core, not 450%.

### Decision 4: Keep MIN_PER_WORKER in auto mode

**Rationale**: The minimum of 25 prevents over-throttling, which could stall the process. This is a safety guard. Users who want absolute control use `-c` (manual mode), which allows values down to 1.

## Risks / Trade-offs

- [Risk] Returning 0.0 on sample failure means the throttler may not send SIGSTOP during the failed sample window → Mitigation: The 5-sample sliding window smooths over single failures; CPU stays near target on subsequent successful samples.
- [Risk] `os.kill(pid, 0)` for zombie detection adds one syscall per throttler iteration → Mitigation: One syscall per 0.2s is negligible overhead.
- [Risk] Changing auto mode calculation may impact users running without any CPU limit configuration → Mitigation: Default CPU_LIMIT is 100, so the new formula multiplies existing budgets by 1.0 (no change for default config).
