## ADDED Requirements

### Requirement: Transcribe media file to text
The system SHALL transcribe audio/video files to text using the external `transcriber` CLI.

#### Scenario: Successful transcription of video file
- **WHEN** a video file path is passed to `save_text()`
- **THEN** the system invokes `transcriber -i <path> -o <output_dir> --format <ext>`
- **THEN** the output text file exists in the output directory

#### Scenario: Unsupported file format returns error
- **WHEN** a non-media file path is passed to `save_text()`
- **THEN** the system SHALL raise a `TranscriberError`

### Requirement: Support multiple output formats
The system SHALL support `txt`, `srt`, `vtt`, and `json` output formats for transcription.

#### Scenario: Text output via save_text(ext="txt")
- **WHEN** `save_text(ext="txt")` is called
- **THEN** the transcriber CLI is invoked with `--format txt`
- **THEN** a `.txt` file with the full transcript is written to the output directory

#### Scenario: SRT subtitle output via save_text(ext="srt")
- **WHEN** `save_text(ext="srt")` is called
- **THEN** the transcriber CLI is invoked with `--format srt`
- **THEN** an `.srt` subtitle file with timestamped segments is written

### Requirement: Streaming/incremental transcription output
The system SHALL support real-time streaming output during transcription when available.

#### Scenario: Streaming output during transcription
- **WHEN** `save_text(incremental=True)` is called
- **THEN** the transcriber CLI is invoked with streaming output enabled
- **THEN** each completed segment is logged at INFO level with start/end timestamps and text

#### Scenario: Graceful fallback when streaming unavailable
- **WHEN** `save_text(incremental=True)` is called but streaming is unavailable
- **THEN** the system falls back to file-based output
- **THEN** a warning is logged

### Requirement: Configurable model selection
The system SHALL allow the transcription model to be configured via environment variable.

#### Scenario: Default model
- **WHEN** `TRANSCRIBER_MODEL` is not set
- **THEN** the system uses `"base"` as the default model

#### Scenario: Custom model via env var
- **WHEN** `TRANSCRIBER_MODEL` is set to `"large-v3"`
- **THEN** the transcriber CLI is invoked with `--model large-v3`

### Requirement: Initial prompt support
The system SHALL support an initial prompt to guide transcription context.

#### Scenario: Custom initial prompt via env var
- **WHEN** `TRANSCRIBER_INITIAL_PROMPT` is set
- **THEN** the transcriber CLI is invoked with `--initial-prompt <value>`

#### Scenario: Default initial prompt
- **WHEN** `TRANSCRIBER_INITIAL_PROMPT` is not set
- **THEN** no `--initial-prompt` flag is passed to transcriber CLI

### Requirement: Clear error on missing transcriber CLI
The system SHALL provide a clear error message when the `transcriber` CLI is not installed.

#### Scenario: transcriber CLI not found
- **WHEN** `save_text()` is called and `transcriber` is not in PATH
- **THEN** a `TranscriberError` is raised with a message instructing installation via `brew install RedAtman/tap/transcriber`
