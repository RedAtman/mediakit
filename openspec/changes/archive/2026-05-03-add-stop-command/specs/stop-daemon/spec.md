## ADDED Requirements

### Requirement: Watch daemon writes PID file
The watch daemon SHALL write its process ID to `~/.mediakit/daemon.pid` when starting.

#### Scenario: PID file written on daemon start
- **WHEN** `mediakit compress --watch` starts
- **THEN** a file at `~/.mediakit/daemon.pid` SHALL contain the daemon's PID

#### Scenario: PID file cleaned up on graceful shutdown
- **WHEN** the daemon exits gracefully (via `mediakit stop` or SIGTERM)
- **THEN** `~/.mediakit/daemon.pid` SHALL be deleted

#### Scenario: Stale PID file does not prevent normal operation
- **WHEN** a stale PID file exists (process no longer running)
- **THEN** the daemon SHALL overwrite it on startup

### Requirement: Graceful stop via `mediakit stop`
The `mediakit stop` command SHALL terminate the running watch daemon gracefully.

#### Scenario: Graceful stop sends SIGTERM
- **WHEN** user runs `mediakit stop`
- **AND** a PID file exists at `~/.mediakit/daemon.pid`
- **THEN** the daemon SHALL receive SIGTERM

#### Scenario: Graceful stop waits for in-flight ffmpeg processes
- **WHEN** the daemon receives SIGTERM
- **AND** ffmpeg processes are currently running
- **THEN** the daemon SHALL wait for those processes to complete before exiting

#### Scenario: Graceful stop prevents new file events
- **WHEN** the daemon receives SIGTERM
- **THEN** the file system observer SHALL stop
- **AND** no new file processing SHALL begin

#### Scenario: No daemon running reports status
- **WHEN** user runs `mediakit stop`
- **AND** no PID file exists at `~/.mediakit/daemon.pid`
- **THEN** the command SHALL report "no running daemon found" and exit successfully

#### Scenario: Stale PID file is handled
- **WHEN** user runs `mediakit stop`
- **AND** a PID file exists but the process is not running
- **THEN** the command SHALL report "no running daemon found", clean up the PID file, and exit successfully

### Requirement: Force stop via `mediakit stop --force`
The `mediakit stop --force` command SHALL immediately terminate the running watch daemon and all its child processes.

#### Scenario: Force stop kills process tree
- **WHEN** user runs `mediakit stop --force`
- **AND** a PID file exists at `~/.mediakit/daemon.pid`
- **THEN** the daemon and all its child processes SHALL receive SIGKILL

#### Scenario: Force stop does not wait for in-flight processes
- **WHEN** user runs `mediakit stop --force`
- **AND** ffmpeg processes are currently running
- **THEN** those processes SHALL be killed immediately

### Requirement: Stop command is discoverable
The `mediakit stop` and `mediakit stop --force` commands SHALL be discoverable via CLI help.

#### Scenario: Stop appears in argument help
- **WHEN** user runs `mediakit --help`
- **THEN** `stop` SHALL appear in the list of valid actions

#### Scenario: Force flag appears in stop help
- **WHEN** user runs `mediakit stop --help`
- **THEN** `--force` SHALL appear as a valid option
