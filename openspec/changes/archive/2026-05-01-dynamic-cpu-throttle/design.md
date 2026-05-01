## Context

The current `cpulimit`‑based approach wraps ffmpeg commands in `cpulimit --limit N --lazy` as a command prefix baked into `BaseMedia._CPULIMIT_PREFIX` at class load time. The limit (`CPULIMIT_LIMIT` from config, default 100) is static for the lifetime of a process. There is no mechanism to adjust CPU usage of already‑running ffmpeg processes in response to system load changes or user intent.

This design replaces `cpulimit` with a self‑contained Python‑based dynamic throttler that uses `SIGSTOP`/`SIGCONT` (the same mechanism cpulimit uses internally) and runs as a daemon thread inside the `media_handler` process. It is cross‑platform (macOS and Linux) with zero additional dependencies.

## Goals / Non-Goals

**Goals:**

- Replace `cpulimit` dependency with an in‑process throttler that supports dynamic per‑process CPU target adjustment
- System load‑aware automatic throttling: reduce ffmpeg CPU budget when the host is busy, expand when idle
- Manual override via `SIGUSR1` and file‑based commands, taking priority over automatic adjustments
- Correctly handle parallel workers (`MAX_WORKERS > 1`) by distributing a global CPU budget across active processes
- Cross‑platform: macOS and Linux, no third‑party Python packages

**Non-Goals:**

- Per‑thread CPU limiting (the throttler operates at process level via `SIGSTOP`/`SIGCONT`)
- Fine‑grained sub‑second duty cycle control (200 ms sampling window is sufficient)
- Integration with Docker cgroups or Linux `systemd` resource control (unnecessary complexity for the use case)

## Decisions

1. **SIGSTOP/SIGCONT over other mechanisms** — The same technique cpulimit uses internally, proven compatible with ffmpeg across both platforms. Alternatives considered:
   - `cgroups` (Linux‑only, requires privileges)
   - `renice` (does not cap CPU, only affects scheduling priority)
   - `setpriority(PRIO_DARWIN_ROLE_BACKGROUND)` (macOS‑only, binary on/off, no percentage control)
   - SIGSTOP/SIGCONT is the only cross‑platform mechanism that provides percentage‑based CPU limiting

2. **Daemon thread over separate process** — Simple to integrate with `CommandExecutor`, shares process lifecycle, no IPC needed. The `TaskManager` in `utils/executor.py` already uses threads, so threading is a proven pattern in this project.

3. **`/proc/[pid]/stat` (Linux) and `proc_pidinfo()` (macOS) over `ps` subprocess** — Subprocess spawning for sampling has high overhead at 200 ms intervals. Both native APIs provide sub‑millisecond CPU time samples. `ps` retained as a fallback if `proc_pidinfo()` is restricted by sandboxing on newer macOS versions.

4. **Sliding window average over instantaneous sampling** — A 5‑sample window (1 second) smooths out ffmpeg's natural CPU fluctuation, preventing rapid SIGSTOP/SIGCONT toggling ("thrashing"). The process is only stopped when the window average exceeds target, and resumed when it falls below 80% of target (hysteresis band).

5. **File‑based manual override (`/tmp/media_handler_cpu_<N>`)** over a control socket — Zero additional infrastructure, trivially scriptable, survives process restarts. Signal handler (`SIGUSR1`) provides quick toggle for interactive use.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `SIGSTOP` during ffmpeg I/O could leave partial files | Tested via existing cpulimit usage — ffmpeg handles `SIGCONT` gracefully; no corruption observed. The SIGSTOP pauses all threads (including I/O), but writes are buffered and flush on resume. |
| `proc_pidinfo()` access restricted on macOS 15+ | Fallback to `ps` subprocess with 1 s sampling granularity (coarser but functional). |
| PID recycling race: throttler sends signal to wrong process after ffmpeg exits | `detach()` is called immediately after `process.communicate()` returns, well before the PID can be recycled. Double‑checked with process start time verification. |
| High thread count with many parallel workers | Each throttler thread sleeps most of the time (200 ms between samples). CPU overhead is negligible (< 0.1% per throttler). At 16 workers, this is ~1.6% total, acceptable. |
| Manual override file name collision (multiple instances) | PID‑suffixed file names: `/tmp/media_handler_cpu_<PID>_<N>`, or better, the file path is configurable. |
| System load awareness could be too aggressive, starving ffmpeg | Min per‑worker floor of 25% ensures throughput doesn't drop to zero. Hysteresis prevents oscillation. |

## Open Questions

- Should the `THROTTLE_INTERVAL` sampling rate be configurable via environment variable? Default 200 ms seems reasonable but power users may want finer control.
- File override path: should it be configurable (via `$MEDIA_HANDLER_THROTTLE_FILE`) or hardcoded to `/tmp/media_handler_cpu_<N>`?
