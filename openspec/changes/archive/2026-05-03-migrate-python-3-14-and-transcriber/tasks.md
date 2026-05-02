## 1. Configuration

- [x] 1.1 Remove `WHISPER_MODEL`, `WHISPER_CPP_MODEL`, `WHISPER_LIB` from `config.py`
- [x] 1.2 Add `TRANSCRIBER_MODEL` (default: `"base"`) to `config.py`
- [x] 1.3 Add `TRANSCRIBER_INITIAL_PROMPT` (default: empty/legacy prompt) to `config.py`

## 2. Transcriber Mixin

- [x] 2.1 Create `src/mixins/transcriber.py` with `MixinMediaTranscriber` class
- [x] 2.2 Implement `save_text()` — shell out to `transcriber -i <path> -o <dir> --format <ext>` via subprocess
- [x] 2.3 Implement streaming/incremental mode — consume transcriber stdout for real-time segment logging
- [x] 2.4 Implement `initial_prompt` passthrough via `--initial-prompt` flag
- [x] 2.5 Implement proper error handling — `TranscriberError` with clear message when CLI missing or fails
- [x] 2.6 Verify LSP diagnostics clean on new file

## 3. Update Base Classes

- [x] 3.1 Update `base/video.py`: replace `MixinMediaFasterWhisper` import with `MixinMediaTranscriber`
- [x] 3.2 Update `base/audio.py`: replace `MixinMediaFasterWhisper` import with `MixinMediaTranscriber`
- [x] 3.3 Remove `src/mixins/whispers.py` (delete file)
- [x] 3.4 Verify LSP diagnostics clean on all changed files

## 4. Update Scheduler & CLI

- [x] 4.1 Review `src/schedulers/folder.py` — `save_text` dispatcher works as-is (dynamic dispatch)
- [x] 4.2 Review `utils/cli.py` — no entry point changes needed
- [x] 4.3 Verify LSP diagnostics clean

## 5. Python Version & Dependencies

- [x] 5.1 Update `requires-python = ">=3.14"` in `pyproject.toml`
- [x] 5.2 Remove `openai-whisper`, `faster-whisper`, `whisper-cpp-pybind` from dependencies in `pyproject.toml` (kept ffmpeg-python for ffmpeg.probe())
- [x] 5.3 Run `uv sync` to regenerate lockfile

## 6. Documentation

- [x] 6.1 Update `README.md`: Python version references (3.12 → 3.14), add transcriber CLI install instructions
- [x] 6.2 Update `README.zh.md`: same changes as 6.1
- [x] 6.3 Update `AGENTS.md` and `src/AGENTS.md` — whisper references → transcriber

## 7. Verification

- [x] 7.1 Run `pdm run lint` — ruff/codespell/vulture pass (pre-existing issues in docs/reference.py only)
- [x] 7.2 Run `pytest -vv` — 65 passed, 6 failed (all pre-existing DB engine property issues), 3 skipped
- [x] 7.3 Transcription unit tests: 6/6 passed
- [x] 7.4 Manual smoke test: `mediakit --help` works, transcriber CLI transcribed silence successfully
