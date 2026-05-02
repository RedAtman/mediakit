## 1. Cross-platform CPU Sampling

- [ ] 1.1 Create `utils/throttle/` package with `__init__.py`
- [ ] 1.2 Implement Linux CPU sampler via `/proc/[pid]/stat` (utime + stime, fields 13/14)
- [ ] 1.3 Implement macOS CPU sampler via `proc_pidinfo()` / `PROC_PIDTASKINFO` using ctypes
- [ ] 1.4 Implement macOS fallback sampler via `ps -p PID -o utime=,stime=`
- [ ] 1.5 Implement system CPU load monitor: `/proc/stat` (Linux) and `os.getloadavg()` (macOS)
- [ ] 1.6 Add unit tests for sampling with mocked `/proc` and `proc_pidinfo`

## 2. ProcessThrottler

- [ ] 2.1 Implement `ProcessThrottler` threading class with PID attachment and daemon flag
- [ ] 2.2 Implement 200 ms sampling loop with sliding window (5 samples) CPU average
- [ ] 2.3 Implement SIGSTOP when window average exceeds target with hysteresis (resume at 80% of target)
- [ ] 2.4 Implement `target` property for runtime CPU limit changes
- [ ] 2.5 Implement zombie detection and cleanup on ESRCH / PID exit
- [ ] 2.6 Add unit tests for throttler logic with mock signals

## 3. CPULimiterCoordinator

- [ ] 3.1 Implement `CPULimiterCoordinator` daemon thread with `attach(pid)` / `detach(pid)` methods
- [ ] 3.2 Implement system load sampling loop (1 s cycle) with load threshold detection (80% / 50% boundaries)
- [ ] 3.3 Implement budget calculation: total budget = cores × load_factor ÷ active_workers, with 25% per-worker floor
- [ ] 3.4 Implement `SIGUSR1` handler cycling through profiles: 100% → 50% → 25% → unlimited
- [ ] 3.5 Implement file-based override reader: scan `/tmp/media_handler_cpu_*` at 2 s interval
- [ ] 3.6 Ensure manual override takes priority over automatic load adjustment
- [ ] 3.7 Add thread safety via `threading.Lock` for shared state (targets, worker set, override flag)

## 4. Integration with CommandExecutor and BaseMedia

- [ ] 4.1 Add optional `coordinator` parameter to `CommandExecutor.execute()`
- [ ] 4.2 Register PID with coordinator after `subprocess.Popen`, deregister after `process.communicate()`
- [ ] 4.3 Remove `_CPULIMIT_PREFIX`, `_CPULIMIT_BIN`, and `cpulimit` logic from `BaseMedia`
- [ ] 4.4 Update `_FFMPEG_PREFIX` to point directly to ffmpeg binary
- [ ] 4.5 Verify `utils/executor.py` TaskManager works correctly with coordinator (no direct changes needed)

## 5. Integrate with Schedulers and Config

- [ ] 5.1 Instantiate `CPULimiterCoordinator` in `src/schedulers/folder.py` at scheduler setup
- [ ] 5.2 Wire `--cpulimit` CLI arg to coordinator default limit
- [ ] 5.3 Remove `CPULIMIT_BIN_DIR` from `config.py`; keep `CPULIMIT_LIMIT` as default
- [ ] 5.4 Set up `SIGUSR1` signal handler in the scheduler entry point
- [ ] 5.5 Update `README.md`: remove `brew install cpulimit` prerequisite, document new throttle mechanisms

## 6. Remove cpulimit Dependency

- [ ] 6.1 Clean up any lingering references to `cpulimit` in `src/schedulers/folder.py`
- [ ] 6.2 Remove `cpulimit` from CLI help text and arg parsing
- [ ] 6.3 Verify no imports or code paths reference `_CPULIMIT_PREFIX` or `_CPULIMIT_BIN`

## 7. Testing and Verification

- [ ] 7.1 Run full test suite (`pytest -vv --rootdir .`) and fix any regressions
- [ ] 7.2 Manual QA: run a compress job, verify SIGUSR1 toggles profiles correctly
- [ ] 7.3 Manual QA: run parallel workers, verify budget distribution
- [ ] 7.4 Manual QA: create override file, verify coordinator reads it
- [ ] 7.5 Verify diagnostics clean (`lsp_diagnostics` on all changed files)
- [ ] 7.6 Run lint suite (`pdm run lint`)
