## ADDED Requirements

### Requirement: Folder file interpretation
The system SHALL read folder paths from a text file specified via `--folder-file` flag. Each line SHALL contain one folder path. Empty lines and lines starting with `#` SHALL be ignored. Leading/trailing whitespace SHALL be stripped from each line. If a line contains only whitespace after stripping, it SHALL be treated as blank and ignored.

#### Scenario: Typical folder file
- **WHEN** the folder file contains `video` paths.txt` with content `# This is a comment\n/media/videos\n\n/photos\n` 
- **THEN** the system SHALL process the paths `/media/videos` and `/photos` and ignore the comment and blank line

### Requirement: Default folder file path
The system SHALL use `CONFIG.WATCH_FOLDER_FILE` as the default when `--folder-file` is not provided. `CONFIG.WATCH_FOLDER_FILE` SHALL resolve to `var/folder.sh` relative to the project root directory.

#### Scenario: No --folder-file flag
- **WHEN** the user runs `mediakit watch -t video` without `--folder-file`
- **THEN** the system SHALL attempt to read paths from `CONFIG.WATCH_FOLDER_FILE`

### Requirement: Fallback when default file missing
The system SHALL fall back to `CONFIG.MEDIA_FILE_FOLDER` when the default `CONFIG.WATCH_FOLDER_FILE` does not exist. The system SHALL log a debug message about the fallback.

#### Scenario: Default file not found
- **WHEN** `CONFIG.WATCH_FOLDER_FILE` does not exist on disk and `--folder-file` was not specified
- **THEN** the system SHALL use `CONFIG.MEDIA_FILE_FOLDER` as the single watched folder and SHALL log a debug message

### Requirement: Nonexistent path in folder file
The system SHALL skip lines referencing paths that do not exist on disk. The system SHALL log a warning for each skipped path and continue processing remaining paths.

#### Scenario: Invalid path in file
- **WHEN** the folder file contains `/media/videos` and `/nonexistent/path`
- **THEN** the system SHALL monitor `/media/videos` and skip `/nonexistent/path` with a warning log

### Requirement: Empty folder file
The system SHALL log a hint when the folder file yields zero valid paths (all lines are comments, blanks, or nonexistent). The watch session SHALL still start but monitor no paths.

#### Scenario: All comments or blanks
- **WHEN** the folder file contains only `# comment` lines and blank lines
- **THEN** the system SHALL log a hint about zero valid paths and SHALL start the watch session with no monitored folders

### Requirement: Multiple observer schedules
The system SHALL create one `watchdog.Observer.schedule()` call per valid folder path from the file. All schedules SHALL share a single Observer instance. All folders SHALL receive the same event handler configuration (`--no-recursive`, `--no-scan-existing`, media type).

#### Scenario: Two paths in folder file
- **WHEN** the folder file contains `/media/videos` and `/media/photos`
- **THEN** the system SHALL create two observer schedules, one watching each path
