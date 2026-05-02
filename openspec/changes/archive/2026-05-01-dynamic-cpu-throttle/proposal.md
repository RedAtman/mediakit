## Why

Currently, CPU utilization of ffmpeg processes is controlled via `cpulimit` wrapped around each command at launch time. The limit is baked into `_FFMPEG_PREFIX` at class load time and cannot be adjusted for running processes. This makes it impossible to dynamically throttle CPU usage in response to system load or user intervention — a significant limitation for a tool that runs unattended batch processing alongside other workloads.

## What Changes

- Replace `cpulimit`‑based CPU limiting with an in‑process dynamic throttler using SIGSTOP/SIGCONT on individual ffmpeg PIDs
- Add a `CPULimiterCoordinator` daemon thread that monitors system load and manages per‑process throttlers
- Support runtime override via `SIGUSR1` signal (quick profile cycling) and file‑based commands (`/tmp/media_handler_cpu_<N>`)
- Remove `CPULIMIT_BIN_DIR` dependency and `_CPULIMIT_PREFIX` from `BaseMedia`
- Ensure the throttler works on both macOS and Linux using platform‑native CPU sampling (`/proc/[pid]/stat` on Linux, `proc_pidinfo()` on macOS)

## Capabilities

### New Capabilities
- `dynamic-cpu-throttle`: Per‑process CPU throttling with real‑time target updates, system load awareness, manual override via signals/files, and dynamic worker budget allocation

### Modified Capabilities

<!-- No existing specs to modify — this is a brand‑new capability -->

## Impact

- **Added**: `utils/throttle/` package with coordinator, per‑process throttler, and cross‑platform CPU sampling
- **Removed**: `cpulimit` binary dependency (`brew install cpulimit` no longer required)
- **Modified**: `base/media.py` — remove `_CPULIMIT_PREFIX` / `_CPULIMIT_BIN`, integrate with coordinator
- **Modified**: `utils/command.py` — `CommandExecutor.execute()` registers PIDs with coordinator
- **Modified**: `config.py` — remove `CPULIMIT_BIN_DIR`, optionally add `THROTTLE_INTERVAL`
- **Modified**: `src/schedulers/folder.py` — instantiate coordinator, wire signal handlers
- **No change**: `utils/executor.py`, `base/video.py`, `base/audio.py` (upstream integration)
