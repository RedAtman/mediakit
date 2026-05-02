## ADDED Requirements

### Requirement: User can start watching a folder
The system SHALL provide a `mediakit watch` CLI command that starts an event-driven watcher on a specified folder.

#### Scenario: Watch command starts and displays status
- **WHEN** user runs `mediakit watch -f /path/to/media`
- **THEN** the system prints a status line "Watching /path/to/media for new media files..." and begins monitoring

#### Scenario: Watch command accepts folder argument
- **WHEN** user runs `mediakit watch -f /path/to/media`
- **THEN** the system monitors the specified folder at `/path/to/media`

#### Scenario: Watch command uses default folder
- **WHEN** user runs `mediakit watch`
- **THEN** the system uses the default folder from `CONFIG.MEDIA_FILE_FOLDER`

### Requirement: New media files are detected via filesystem events
The system SHALL use `watchdog.Observer` to detect newly created files in the watched folder.

#### Scenario: File created in watched folder triggers detection
- **WHEN** a new file appears in the watched folder
- **THEN** the system detects it via the `on_created` event

#### Scenario: Directory creation does not trigger processing
- **WHEN** a new subdirectory is created in the watched folder
- **THEN** the system ignores the directory creation event

### Requirement: Recursive monitoring is configurable
The system SHALL support `--no-recursive` flag to control subdirectory monitoring, defaulting to non-recursive.

#### Scenario: Default is non-recursive
- **WHEN** user runs `mediakit watch -f /path/to/media` without `--no-recursive`
- **THEN** the system monitors ONLY the specified directory, not subdirectories

#### Scenario: Recursive flag enables subdirectory monitoring
- **WHEN** user runs `mediakit watch -f /path/to/media --no-recursive`
- **THEN** the system does NOT monitor subdirectories (explicit off)

#### Scenario: Recursive is already the default (no-op confirmation)
- **WHEN** user runs `mediakit watch -f /path/to/media`
- **THEN** subdirectories are NOT monitored by default

### Requirement: File stability is checked before processing
The system SHALL verify a new file is stable (fully written) before adding it to the processing pipeline.

#### Scenario: File size stabilizes
- **WHEN** a new file is detected and its size remains unchanged for 3 consecutive 1-second samples
- **THEN** the system considers the file stable and proceeds with processing

#### Scenario: File still writing after timeout
- **WHEN** a new file is detected but its size keeps changing for 30 seconds
- **THEN** the system processes the file anyway after the timeout

### Requirement: Burst arrivals are debounced
The system SHALL batch new files arriving in quick succession, dispatching them after a calm period.

#### Scenario: Multiple files arrive within 5 seconds
- **WHEN** 50 files are created in the watched folder within 3 seconds
- **THEN** the system buffers all 50 files and dispatches them together after 5 seconds of no new events

#### Scenario: Single file is dispatched after calm period
- **WHEN** a single file is created and no new events occur for 5 seconds
- **THEN** the system dispatches the file for processing after the calm period

#### Scenario: Maximum flush interval
- **WHEN** files keep arriving continuously for 60 seconds without a calm period
- **THEN** the system flushes the buffer and processes all buffered files

### Requirement: Existing files are scanned at startup
The system SHALL scan the folder for existing media files at startup and process them.

#### Scenario: Existing media files found at startup
- **WHEN** user runs `mediakit watch -f /path/to/media` and the folder contains 10 media files
- **THEN** the system processes all 10 existing media files

#### Scenario: Existing scan can be disabled
- **WHEN** user runs `mediakit watch -f /path/to/media --no-scan-existing`
- **THEN** the system skips processing existing files and only watches for new ones

### Requirement: Media type filtering is supported
The system SHALL accept the `-t`/`--type` argument to filter by media type.

#### Scenario: Filter by video type
- **WHEN** user runs `mediakit watch -f /path -t video`
- **THEN** only video files are processed

#### Scenario: Default type is all
- **WHEN** user runs `mediakit watch -f /path` without `-t`
- **THEN** all media types are processed (default)

### Requirement: Parallel workers are supported
The system SHALL accept the `-w`/`--max_workers` argument to control parallel processing.

#### Scenario: Workers specified
- **WHEN** user runs `mediakit watch -f /path -w 4`
- **THEN** up to 4 files are processed in parallel

#### Scenario: Default workers
- **WHEN** user runs `mediakit watch -f /path` without `-w`
- **THEN** the default worker count from configuration is used

### Requirement: CPU throttling is supported
The system SHALL accept the `-c`/`--cpu-limit` argument to throttle CPU usage.

#### Scenario: CPU limit specified
- **WHEN** user runs `mediakit watch -f /path -c 50`
- **THEN** CPU usage is throttled to 50%

### Requirement: Duplicate detection prevents reprocessing
The system SHALL check the database before processing to avoid re-processing files that have already been processed.

#### Scenario: New file not in database
- **WHEN** a new file is detected and it does not exist in the media database
- **THEN** the system adds it to the database and processes it

#### Scenario: File already in database
- **WHEN** a new file is detected but it already exists in the media database (same path)
- **THEN** the system skips processing that file

### Requirement: Processed files are soft-removed
The system SHALL soft-remove (move to trash) processed media files.

#### Scenario: Successfully processed file is removed
- **WHEN** a file is successfully processed
- **THEN** the file is moved to the trash directory

### Requirement: Running watch can be interrupted gracefully
The system SHALL handle SIGINT (Ctrl+C) gracefully, finishing in-progress tasks before exiting.

#### Scenario: Ctrl+C during watch
- **WHEN** user presses Ctrl+C while mediakit watch is running
- **THEN** the system finishes processing current in-progress tasks and exits cleanly

#### Scenario: In-progress tasks are completed
- **WHEN** user presses Ctrl+C while files are being compressed
- **THEN** the running compressions complete before the process exits

### Requirement: Watcher output shows processing status
The system SHALL display both real-time progress bars and periodic log lines.

#### Scenario: Progress bar shown during processing
- **WHEN** files are being processed
- **THEN** a progress bar shows the current task (reuse existing progress from `utils/progress.py`)

#### Scenario: Log line printed at start of each batch
- **WHEN** a batch of files is dispatched for processing
- **THEN** a log line prints: "[timestamp] Processing N files..."

#### Scenario: Log line printed at completion
- **WHEN** a batch of files finishes processing
- **THEN** a log line prints: "[timestamp] Finished processing N files (S succeeded, F failed)"

### Requirement: Observer health is monitored
The system SHALL periodically verify the Observer is alive and restart it if necessary.

#### Scenario: Observer dies
- **WHEN** the watchdog Observer thread stops unexpectedly
- **THEN** the system restarts the Observer within 30 seconds
