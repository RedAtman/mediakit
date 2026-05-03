## 1. CLI Setup

- [x] 1.1 Add `stop` to `mapper_action` in `utils/cli.py`
- [x] 1.2 Add `--force` flag to argument parser (only applicable when action is `stop`). Note: `-f` short option was intentionally dropped due to conflict with existing `-f/--folder`.

## 2. Stop Command Implementation

- [x] 2.1 Create `_stop()` function in `src/schedulers/folder.py` as a `_SimpleScheduler` that reads `~/.mediakit/daemon.pid`, verifies the process exists with `kill -0`, and sends SIGTERM (graceful) or SIGKILL + `killpg` (force)

## 3. PID File Lifecycle in WatcherScheduler

- [x] 3.1 Create `~/.mediakit/` directory if it doesn't exist and write PID on watch startup (before `_run_event_loop`)
- [x] 3.2 Clean up PID file in a `finally` block after `_run_event_loop` completes (graceful exit only)

## 4. Enhanced Graceful Shutdown in WatcherScheduler

- [x] 4.1 Add `_inflight_batch` (threading.Event) to track whether a `_flush_callback` batch is in progress
- [x] 4.2 Set the event before `Folder.run__()` and clear it after in `_flush_callback`
- [x] 4.3 Enhance `_signal_handler`: after stopping observer, wait for `_inflight_batch` to clear before returning
- [x] 4.4 Register SIGTERM handler (SIGINT handler already exists)

## 5. Verify

- [x] 5.1 Run linter and typecheck on all changed files. Results: only pre-existing F841/E402 errors remain.
- [x] 5.2 Run existing test suite to confirm no regressions. Results: 127/127 tests pass.

## 6. Documentation

- [x] 6.1 Update README.md and README.zh.md with stop command usage
- [x] 6.2 Update AGENTS.md with stop command and updated test count
