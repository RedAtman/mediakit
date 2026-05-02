## Why

Python 3.14 support is blocked by the whisper library stack (openai-whisper, faster-whisper) which depends on Numba/PyAV/onnxruntime — none of which support Python 3.14. Additionally, ffmpeg-python==0.2.0 has CVE-2025-50817 via its unmaintained 'future' dependency. Migrating to an external `transcriber` CLI (whisper.cpp-based, Rust) eliminates all of these Python-level dependencies, unblocks Python 3.14, and provides a faster, more reliable transcription path.

## What Changes

- **Remove** Python whisper dependencies: openai-whisper, faster-whisper, whisper-cpp-pybind, ffmpeg-python
- **Add** `transcriber` CLI as external dependency (Homebrew tap: RedAtman/tap)
- **Rewrite** `src/mixins/whispers.py` → `src/mixins/transcriber.py` — single `MixinMediaTranscriber` that shells out to the CLI
- **Update** `base/video.py` and `base/audio.py` to use new transcriber mixin
- **Simplify** `save_text` — returns boolean success instead of parsed dict
- **Remove** old config vars (`WHISPER_MODEL`, `WHISPER_CPP_MODEL`, `WHISPER_LIB`); add `TRANSCRIBER_MODEL`
- **Update** `pyproject.toml`: `requires-python = ">=3.14"`, drop removed dependencies
- **Regenerate** lockfile with `uv lock`
- **Update** README references from Python 3.12 to 3.14
- Accept **BREAKING**: `save_text` return type changes from dict to bool

## Capabilities

### New Capabilities
- `transcription`: Speech-to-text via external `transcriber` CLI (whisper.cpp-based). Supports streaming output and initial_prompt. Replaces the old Python whisper stack entirely.

### Modified Capabilities

None — no existing specs to modify.

## Impact

- **Files removed**: `src/mixins/whispers.py` (199 lines, 3 mixin classes)
- **Files rewritten**: `base/video.py` (mixin import), `base/audio.py` (mixin import)
- **Files created**: `src/mixins/transcriber.py` (new mixin)
- **Config changed**: `config.py` (whisper vars → transcriber var)
- **Scheduler**: `src/schedulers/folder.py` (`save_text` dispatcher unchanged, method signature changes)
- **CLI**: `utils/cli.py` (`save_text` entry point)
- **Dependencies**: `pyproject.toml` (requires-python bump, 4 deps removed)
- **Lockfile**: `uv.lock` (regenerate)
- **Docs**: `README.md`, `README.zh.md`
- **User-facing**: Users must `brew install RedAtman/tap/transcriber`; old whisper env vars obsolete
