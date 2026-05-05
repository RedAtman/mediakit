## ADDED Requirements

### Requirement: Watch-mode processing updates media state to finished
The system SHALL update the DB state of a media file to `finished(2)` after successful compression in watch mode (both `_feed_existing` and `_flush_callback` paths).

#### Scenario: Successful compression via _feed_existing
- **WHEN** watch mode starts and processes an existing unprocessed file via `_feed_existing`
- **AND** the ffmpeg compression exits with code 0
- **THEN** the media's DB state SHALL be updated to `{"compress": 2.0, ...}`
- **AND** the media file SHALL be moved to the `.removed/` subdirectory

#### Scenario: Successful compression via _flush_callback
- **WHEN** a new file is added to the watched folder and triggers `_flush_callback`
- **AND** the ffmpeg compression exits with code 0
- **THEN** the media's DB state SHALL be updated to `{"compress": 2.0, ...}`
- **AND** the media file SHALL be moved to the `.removed/` subdirectory

### Requirement: Watch-mode processing updates media state to failed
The system SHALL update the DB state of a media file to `failed(-2)` after failed compression in watch mode.

#### Scenario: Failed compression via _feed_existing
- **WHEN** watch mode processes an existing file via `_feed_existing`
- **AND** the ffmpeg compression exits with non-zero code or raises an exception
- **THEN** the media's DB state SHALL be updated to `{"compress": -2.0, ...}`
- **AND** the media file SHALL NOT be moved

#### Scenario: Failed compression via _flush_callback
- **WHEN** a new file triggers `_flush_callback`
- **AND** the ffmpeg compression exits with non-zero code or raises an exception
- **THEN** the media's DB state SHALL be updated to `{"compress": -2.0, ...}`
- **AND** the media file SHALL NOT be moved

### Requirement: Watch-mode callbacks receive Result objects
The system SHALL wrap media processing results in `response.Result` objects when called through watch mode paths, matching the non-watch path behavior.

#### Scenario: _batch_callback receives Result object
- **WHEN** a media compression task completes in watch mode
- **THEN** the `_batch_callback` SHALL receive a `response.Result` object via `future.result()`
- **AND** `hasattr(result, 'data')` SHALL be `True`
- **AND** `result.data.get('media')` SHALL return the media object
- **AND** `result == 0` SHALL evaluate correctly for success/failure
