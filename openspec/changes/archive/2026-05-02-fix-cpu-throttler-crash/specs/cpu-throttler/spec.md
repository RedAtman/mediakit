## ADDED Requirements

### Requirement: Throttler survives sampling failures
The CPU throttler SHALL remain operational after a single CPU sampling failure.

#### Scenario: Single proc_pidinfo failure does not kill throttler
- **WHEN** `_macos_proc_pidinfo()` raises `ProcessLookupError` for one sample
- **THEN** the throttler SHALL log the failure and continue sampling on the next cycle
- **THEN** the throttler SHALL NOT mark itself as zombie

#### Scenario: Persistent sampling failures are handled gracefully
- **WHEN** `_macos_proc_pidinfo()` AND `_macos_ps_fallback()` both fail for a sample
- **THEN** `macos_sample_cpu_time()` SHALL return 0.0
- **THEN** the throttler SHALL log a warning with the failure details

### Requirement: Throttler detects genuinely dead processes
The throttler SHALL detect when the tracked process has actually exited and stop itself.

#### Scenario: Process exit causes throttler to terminate
- **WHEN** the tracked PID no longer exists (process exited)
- **THEN** the throttler SHALL detect this within 5 seconds
- **THEN** the throttler SHALL clean up and exit

### Requirement: CPU sampling fallback chain works end-to-end
The CPU sampling system SHALL attempt sampling via `proc_pidinfo()` first, then fall back to `ps` subprocess.

#### Scenario: proc_pidinfo fails, ps fallback succeeds
- **WHEN** `proc_pidinfo()` fails with `ProcessLookupError`
- **THEN** `macos_sample_cpu_time()` SHALL try `_macos_ps_fallback()`
- **THEN** if `ps` succeeds, the return value SHALL be the correct CPU time

#### Scenario: Both sampling methods fail
- **WHEN** `proc_pidinfo()` fails with `ProcessLookupError` AND `ps` subprocess times out or fails
- **THEN** `macos_sample_cpu_time()` SHALL return 0.0
- **THEN** a warning SHALL be logged

### Requirement: Auto-mode CPU_LIMIT applies at all load levels
The CPU throttler SHALL respect `CPU_LIMIT` across all system load conditions in auto mode.

#### Scenario: High load with CPU_LIMIT=1
- **WHEN** system load > 80% AND `CPU_LIMIT=1`
- **THEN** the per-worker target SHALL be proportionally reduced by the CPU_LIMIT factor
- **THEN** the calculated budget SHALL be clamped to a minimum of 25%

#### Scenario: Moderate load with CPU_LIMIT=50
- **WHEN** system load is 50-80% AND `CPU_LIMIT=50`
- **THEN** the per-worker target SHALL be proportionally reduced by the CPU_LIMIT factor

#### Scenario: Default CPU_LIMIT=100 produces same behavior as before
- **WHEN** `CPU_LIMIT=100` (default) AND system load > 50%
- **THEN** the calculated budget SHALL be the same as before this change

### Requirement: Manual override (-c flag) unchanged
The manual override via `-c/--cpu-limit` CLI flag SHALL continue working as before.

#### Scenario: -c 1 overrides all auto mode calculations
- **WHEN** `-c 1` is passed
- **THEN** `set_manual_override(1)` SHALL be called
- **THEN** `_manual_override_active` SHALL be True
- **THEN** the per-worker target SHALL be exactly 1% (clamped to minimum 1)

### Requirement: SIGUSR1 cycling works reliably across throttler lifetime
Multiple SIGUSR1 signals SHALL each cycle to the next profile in [None, 100, 50, 25].

#### Scenario: Three consecutive SIGUSR1 signals
- **WHEN** throttler has been running for the entire ffmpeg duration
- **WHEN** three SIGUSR1 signals are sent sequentially
- **THEN** each signal SHALL cycle the profile to the next value
- **THEN** the target SHALL be applied to the active throttler
- **THEN** the throttler SHALL NOT crash after any signal

### Requirement: Active throttlers appear in coordinator's throttlers dict
The coordinator SHALL maintain accurate tracking of active throttlers.

#### Scenario: Throttler attached and not crashed
- **WHEN** `attach(pid)` is called
- **THEN** a `ProcessThrottler` SHALL be created and stored in `_throttlers`
- **WHEN** `_apply_target_to_all()` is called
- **THEN** all entries in `_throttlers` SHALL receive the updated target
- **WHEN** `detach(pid)` is called
- **THEN** the throttler SHALL be removed from `_throttlers`
