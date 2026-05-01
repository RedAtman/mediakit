## ADDED Requirements

### Requirement: Per-process CPU target adjustment
The system SHALL allow the CPU usage target for each running ffmpeg process to be adjusted at runtime without restarting the process.

#### Scenario: Dynamic limit update
- **WHEN** the CPULimiterCoordinator updates the target CPU percentage for a throttler
- **THEN** the throttler adjusts its SIGSTOP/SIGCONT duty cycle within the next sampling window

#### Scenario: No restart required
- **WHEN** the CPU target changes
- **THEN** the target change MUST take effect on the currently running ffmpeg process without terminating or restarting it

### Requirement: System load-aware automatic throttling
The system SHALL monitor host CPU load and automatically reduce ffmpeg CPU budget when the system is busy.

#### Scenario: High system load triggers throttling
- **WHEN** host CPU load exceeds 80% for more than 5 consecutive seconds
- **THEN** the total CPU budget for all ffmpeg workers SHALL be reduced to 25% per CPU core

#### Scenario: Moderate system load triggers moderate throttling
- **WHEN** host CPU load is between 50% and 80%
- **THEN** the total CPU budget SHALL be reduced to 50% per CPU core

#### Scenario: System recovers from high load
- **WHEN** host CPU load drops below 50% for more than 10 consecutive seconds
- **THEN** the total CPU budget SHALL return to 100% per CPU core

### Requirement: Manual override with priority
The system SHALL support user-initiated manual overrides that take priority over automatic system load adjustments.

#### Scenario: Signal-based override
- **WHEN** the process receives SIGUSR1
- **THEN** the coordinator SHALL cycle through predefined CPU profiles (100%, 50%, 25%, unlimited)
- **AND** the override SHALL persist until explicitly cleared or the process exits

#### Scenario: File-based override
- **WHEN** a file matching `/tmp/media_handler_cpu_<N>` exists
- **THEN** the coordinator SHALL read `<N>` as the total CPU budget percentage
- **AND** it SHALL distribute this budget equally among active workers

#### Scenario: Manual override takes precedence
- **WHEN** a manual override is active
- **THEN** automatic system load adjustments SHALL be suspended
- **AND** the override SHALL remain in effect until cleared

### Requirement: Fair budget distribution across workers
When multiple ffmpeg workers are running concurrently, the total CPU budget SHALL be distributed evenly.

#### Scenario: Equal distribution
- **WHEN** the total CPU budget is 200% and there are 4 active workers
- **THEN** each worker SHALL receive a target of 50% CPU

#### Scenario: Minimum per-worker floor
- **WHEN** the equal distribution would result in a per-worker target below 25%
- **THEN** each worker SHALL receive a minimum of 25% CPU

### Requirement: Cross-platform CPU sampling
The system SHALL accurately measure per-process CPU time on both macOS and Linux without third-party dependencies.

#### Scenario: Linux CPU sampling
- **WHEN** running on Linux
- **THEN** CPU time SHALL be read from `/proc/[pid]/stat` fields 13 and 14 (utime + stime)

#### Scenario: macOS CPU sampling
- **WHEN** running on macOS
- **THEN** CPU time SHALL be read via `proc_pidinfo()` with `PROC_PIDTASKINFO` flavor

#### Scenario: Graceful fallback on macOS
- **WHEN** `proc_pidinfo()` is unavailable or returns an error
- **THEN** the system SHALL fall back to `ps -p PID -o utime=,stime=`
- **AND** it SHALL log a warning about reduced sampling precision

### Requirement: Throttler cleanup on process exit
Each throttler SHALL be automatically cleaned up when its associated ffmpeg process exits.

#### Scenario: Automatic detach
- **WHEN** a ffmpeg process terminates (any exit code)
- **THEN** the corresponding throttler SHALL stop sampling and be removed from the coordinator

#### Scenario: Stale PID protection
- **WHEN** a throttler detects that its PID no longer exists (OSError ESRCH)
- **THEN** the throttler SHALL mark itself as zombie
- **AND** the coordinator SHALL remove it on the next cleanup cycle
