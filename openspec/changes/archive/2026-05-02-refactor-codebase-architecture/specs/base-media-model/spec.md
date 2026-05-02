## ADDED Requirements

### Requirement: Video-specific properties move from BaseMedia to Video
Metadata properties that assume video stream structure SHALL be defined on Video, not BaseMedia.

#### Scenario: frames_count returns NotImplementedError on Audio
- **WHEN** `frames_count` is accessed on an Audio instance
- **THEN** `NotImplementedError` SHALL be raised
- **WHEN** `frames_count` is accessed on a Video instance
- **THEN** the video frame count SHALL be returned

#### Scenario: width_height returns NotImplementedError on Audio
- **WHEN** `width_height` is accessed on an Audio instance
- **THEN** `NotImplementedError` SHALL be raised

#### Scenario: bitrate returns NotImplementedError on Audio
- **WHEN** `bitrate` is accessed on an Audio instance
- **THEN** `NotImplementedError` SHALL be raised

#### Scenario: duration returns NotImplementedError on Audio
- **WHEN** `duration` is accessed on an Audio instance
- **THEN** `NotImplementedError` SHALL be raised

### Requirement: Video.combine() is decomposed by concern
The `combine()` method SHALL be refactored from a single 167L method into focused strategy classes.

#### Scenario: combine() public API unchanged
- **WHEN** `Video.combine()` is called with existing parameters
- **THEN** the result SHALL be identical to the previous implementation
- **THEN** the method signature SHALL NOT change

#### Scenario: Strategy classes are independently testable
- **WHEN** any extracted strategy class is instantiated
- **THEN** it SHALL accept (cmd_list, params) and modify cmd_list in place
- **THEN** it SHALL be testable without invoking ffmpeg

### Requirement: FFmpeg command building uses unified pattern
Both Video and Audio SHALL use the same command building approach.

#### Scenario: Audio command building uses list-based approach
- **WHEN** Audio builds an ffmpeg command
- **THEN** it SHALL use a list-of-strings approach (not f-strings)
- **THEN** the generated command SHALL be functionally identical to before

#### Scenario: Shared builder utilities extracted
- **WHEN** common ffmpeg argument patterns are identified
- **THEN** they SHALL be extracted to a shared utility
- **THEN** both Video and Audio SHALL use the shared utility
