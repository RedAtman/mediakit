## ADDED Requirements

### Requirement: Watcher detects WATCH_FOLDER_FILE modifications at runtime
The watcher daemon SHALL periodically check the resolved WATCH_FOLDER_FILE (or `--folder-file`) for modifications and reconcile the set of watched directories accordingly.

#### Scenario: Config file modified with new directory added
- **WHEN** a new directory path is appended to WATCH_FOLDER_FILE and saved
- **THEN** within 10 seconds, the watcher SHALL begin monitoring that directory for file events
- **AND** the watcher SHALL scan that directory for existing unprocessed media files and queue them for processing
- **AND** the watcher SHALL log an info message indicating the new directory is now being watched

#### Scenario: Config file modified with directory removed
- **WHEN** an existing directory path is removed from WATCH_FOLDER_FILE and saved
- **THEN** within 10 seconds, the watcher SHALL stop monitoring that directory for new file events
- **AND** the watcher SHALL log an info message indicating the directory is no longer watched

#### Scenario: Config file modified with both additions and removals
- **WHEN** multiple directories are both added and removed in a single edit of WATCH_FOLDER_FILE
- **THEN** the watcher SHALL handle both operations atomically within a single poll cycle

#### Scenario: Config file modified but no path changes
- **WHEN** WATCH_FOLDER_FILE is modified (mtime changes) but the content results in the same set of valid directories
- **THEN** the watcher SHALL make no changes to the observed watch list

### Requirement: Config file polling does not block media processing
The config file polling mechanism SHALL NOT interfere with media file event detection or batch processing.

#### Scenario: Config poll during active media processing
- **WHEN** a batch of media files is being processed (`_flush_callback` active)
- **AND** WATCH_FOLDER_FILE is modified
- **THEN** the config change SHALL be applied without interrupting the in-flight media processing

### Requirement: Graceful handling of config file errors

#### Scenario: Config file temporarily missing
- **WHEN** WATCH_FOLDER_FILE is deleted or renamed
- **THEN** the watcher SHALL log an info message
- **AND** the watcher SHALL maintain all current watches unchanged
- **AND** when the file is re-created, the watcher SHALL resume monitoring it

#### Scenario: Config file has invalid content
- **WHEN** WATCH_FOLDER_FILE is rewritten with non-UTF-8 content or unparseable format
- **THEN** the watcher SHALL log a warning
- **AND** the watcher SHALL maintain all current watches unchanged
- **AND** the watcher SHALL retry on the next poll cycle

#### Scenario: New directory path does not exist
- **WHEN** a new path added to WATCH_FOLDER_FILE does not correspond to an existing directory
- **THEN** the watcher SHALL NOT schedule a watch for that path
- **AND** the watcher SHALL log a warning (matching existing behavior for startup path validation)
