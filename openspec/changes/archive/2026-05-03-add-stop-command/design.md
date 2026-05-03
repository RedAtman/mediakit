## Context

Mediakit CLI dispatches actions via `mapper_action` → `src/schedulers/folder.py`. Long-running watch mode (`WatcherScheduler`) runs indefinitely with a file-system observer. Currently, termination is only possible via raw signals (SIGINT/SIGTERM). No PID file mechanism exists.

Key constraints:
- Watch mode only (non-watch commands are one-shot and don't need stopping)
- Existing `WatcherScheduler` already has `_stop_event` + signal handlers
- `CommandExecutor` tracks ffmpeg PIDs via `CPULimiterCoordinator.attach/detach`
- No PID file support anywhere in the codebase

## Goals / Non-Goals

**Goals:**
- `mediakit stop` sends SIGTERM to the running watch daemon → graceful drain
- `mediakit stop --force` sends SIGKILL to entire process tree → immediate halt
- PID file at `~/.mediakit/daemon.pid` written on watch start, cleaned up on graceful exit
- Graceful drain waits for in-flight ffmpeg subprocesses to complete
- Minimal changes to existing code; no new dependencies

**Non-Goals:**
- Stopping non-watch commands (compress/scale without `--watch`)
- Multi-instance tracking (only one daemon PID file)
- Remote stop or network-based control
- Heartbeat or health-check mechanisms

## Decisions

### D1: PID file at `~/.mediakit/daemon.pid`
The directory `~/.mediakit/` follows XDG convention for user-level runtime metadata. A single file is sufficient since only one watch daemon is expected.

Alternatives considered:
- `/tmp/mediakit.pid` — less stable (cleared on reboot, but that's fine). Chose `~/.mediakit/` to avoid collisions and keep it alongside any future mediakit user config.

### D2: Graceful stop via SIGTERM → `_stop_event` + wait for in-flight
The existing `WatcherScheduler._signal_handler` already:
1. Sets `self._stop_event`
2. Stops the file observer
3. Cleans up `self.task_manager`

We augment it to:
- Track running flush tasks via a `threading.Event` or counter
- Wait for the currently executing `_flush_callback` batch to complete before exiting
- Clean up PID file in a `finally` block

### D3: Force stop via SIGKILL to process group
`--force` uses `os.killpg(os.getpgid(pid), signal.SIGKILL)` to kill the daemon and all child ffmpeg processes. This is reliable on macOS since ffmpeg stays in the same process group by default.

Alternatives considered:
- `pgrep -P` tree traversal + SIGKILL each — more complex, less reliable
- `pkill -P` — not portable across all Unix variants

### D4: `stop` as `_SimpleScheduler` in `src/schedulers/folder.py`
Follows the existing pattern used by `scale`, `convert_format`, `save_text` etc. The `stop` function reads the PID file and sends the appropriate signal, bypassing the media pipeline entirely.

## Risks / Trade-offs

- Orphaned PID file if the daemon is killed with SIGKILL (not via `stop`): mitigated by checking process existence before acting; stale PID is harmless
- Race condition: `stop` runs between PID write and file cleanup: mitigated by checking `/proc/<pid>` (or `kill -0 <pid>`) before sending the real signal
- Multiple watch daemons: not supported by single PID file — trade-off accepted per non-goals
- On macOS: `killpg(SIGKILL)` kills the entire process group, which may include unrelated children. Low risk since daemon starts fresh in its own group.

## Migration Plan

No migration needed — this is a net-new feature. The PID file is created only by the new code path; existing watcher instances from before this change won't have one and `mediakit stop` will report "no running daemon found."
