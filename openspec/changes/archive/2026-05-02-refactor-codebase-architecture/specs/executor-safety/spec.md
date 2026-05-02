## ADDED Requirements

### Requirement: Subprocess execution has configurable timeout
The CommandExecutor SHALL support a configurable timeout for ffmpeg subprocess execution.

#### Scenario: Timeout not set (default)
- **WHEN** `CommandExecutor.execute()` is called without a timeout
- **THEN** the subprocess SHALL run until completion with no time limit
- **THEN** behavior SHALL be identical to the current implementation

#### Scenario: Timeout set and process finishes within limit
- **WHEN** `CommandExecutor.execute()` is called with a timeout
- **WHEN** the subprocess completes before the timeout expires
- **THEN** the result SHALL be returned normally

#### Scenario: Timeout exceeded
- **WHEN** `CommandExecutor.execute()` is called with a timeout
- **WHEN** the subprocess exceeds the timeout
- **THEN** the subprocess SHALL be terminated
- **THEN** a clear error SHALL be raised indicating timeout

### Requirement: Pre-flight disk space check
The CommandExecutor SHALL check available disk space before launching ffmpeg.

#### Scenario: Sufficient disk space available
- **WHEN** `CommandExecutor.execute()` is called
- **WHEN** available disk space exceeds the minimum threshold
- **THEN** the subprocess SHALL launch normally

#### Scenario: Insufficient disk space
- **WHEN** `CommandExecutor.execute()` is called
- **WHEN** available disk space is below the minimum threshold
- **THEN** a clear error SHALL be raised before any subprocess is launched
- **THEN** the error message SHALL include the available space and minimum required

### Requirement: TaskManager cleans up on KeyboardInterrupt
The TaskManager SHALL properly release resources when interrupted via Ctrl+C.

#### Scenario: Ctrl+C during parallel task execution
- **WHEN** parallel tasks are running via TaskManager
- **WHEN** a KeyboardInterrupt is received
- **THEN** `shutdown()` SHALL be called
- **THEN** all worker threads SHALL be joined
- **THEN** all semaphore resources SHALL be released
