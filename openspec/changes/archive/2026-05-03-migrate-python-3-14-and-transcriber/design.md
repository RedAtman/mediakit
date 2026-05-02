## Context

mediakit currently runs on Python 3.12 with a Python-based whisper stack (openai-whisper, faster-whisper, whisper-cpp-pybind) for speech-to-text transcription. All three whisper libraries depend on Numba/PyAV/onnxruntime — none of which support Python 3.14. Additionally, ffmpeg-python==0.2.0 carries CVE-2025-50817 via its unmaintained 'future' dependency.

The solution is to replace all Python whisper libraries with the `transcriber` CLI — a standalone Rust binary (whisper.cpp-based, Homebrew tap: `RedAtman/tap`) that eliminates the entire Python dependency chain blocking the 3.14 migration.

## Goals / Non-Goals

**Goals:**
- Python 3.14 compatibility (`requires-python = ">=3.14"`)
- Remove all Python whisper dependencies (openai-whisper, faster-whisper, whisper-cpp-pybind)
- Remove ffmpeg-python (CVE-2025-50817)
- Single simplified mixin replacing three current whisper mixin classes
- Transparent transcription quality (whisper.cpp is same underlying model)
- Streaming/incremental output and initial_prompt support via transcriber CLI

**Non-Goals:**
- No changes to compress/scale/trim functionality
- No changes to the DB layer or SQLAlchemy models
- No changes to the MiddlewareScheduler pattern
- No changes to CLI argument parsing (save_text entry point preserved)

## Decisions

### 1. External CLI over Python library for transcription
- **Why**: The entire Python whisper dependency chain (Numba → LLVM, PyAV, onnxruntime) blocks Python 3.14 and causes recurring build failures. whisper.cpp (Rust) compiles to a single binary with zero Python dependencies.
- **Alternative considered**: Pinning older Python 3.12 and maintaining whisper stack — rejected because it prevents language upgrades and CVE fixes.
- **Alternative considered**: Switching to a different Python STT library (e.g., vosk, speechbrain) — rejected because all have similar NumPy/PyTorch dependency issues.

### 2. Single MixinMediaTranscriber replacing three mixin classes
- **Current**: `MixinMediaWhisper`, `MixinMediaFasterWhisper`, `MixinMediaWhisperCPP` in `src/mixins/whispers.py` — 199 lines, 3 implementations of similar functionality.
- **New**: Single `MixinMediaTranscriber` in `src/mixins/transcriber.py` — calls external CLI via subprocess.
- **Why**: The three mixins existed because each Python library had a different API. With a single CLI interface, one implementation suffices.
- **Why simpler**: No model loading, no LRU cache of model instances, no per-library kwargs plumbing.

### 3. Config: WHISPER_* vars → TRANSCRIBER_MODEL
- **Old**: `WHISPER_MODEL`, `WHISPER_CPP_MODEL`, `WHISPER_LIB` — 3 env vars reflecting the fragmented library landscape.
- **New**: `TRANSCRIBER_MODEL` (default: `"base"`) — single env var. The transcriber CLI manages model downloading internally (like whisper.cpp's automatic model fetch).
- **New**: `TRANSCRIBER_INITIAL_PROMPT` (optional) — replaces the hardcoded Chinese commercial phrase in whispers.py.
- **Why**: With one CLI backend, one model config suffices.

### 4. save_text returns bool instead of dict
- **Old**: `save_text()` returns `{"language": str, "text": str, "segments": [...]}` — a parsed dict that no internal caller uses.
- **New**: `save_text()` returns `True` on success, raises on failure.
- **Why**: The transcriber CLI writes output files directly (`-o outdir`). Parsing the JSON back into Python just to re-serialize is wasted work. The scheduler (`_SimpleScheduler`) only needs to know success/failure.
- **BREAKING**: Any external code calling `media.save_text()` and using the return dict will break. No such callers exist in the codebase.

### 5. Streaming/incremental mode via subprocess stdout
- **Current**: `MixinMediaFasterWhisper.save_text(incremental=True)` iterates in-process Python segments.
- **New**: transcriber CLI supports streaming JSON-lines output to stdout. The mixin consumes stdout line-by-line for real-time progress logging, matching the old incremental behavior.
- **Why**: No polling files or complex IPC — subprocess pipe is the simplest streaming mechanism.
- **Fallback**: If transcriber doesn't support streaming for the requested format, fall back to file-based output.

### 6. CLI interface mapping
- `transcriber -i <input> -o <outdir> --format <ext>` replaces the Python in-process calls
- `--initial-prompt <text>` maps to the current `initial_prompt` kwarg (now `TRANSCRIBER_INITIAL_PROMPT` config)
- `--model <name>` maps to `TRANSCRIBER_MODEL`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| transcriber CLI not installed | Clear error message: "transcriber CLI not found. Install: brew install RedAtman/tap/transcriber" |
| transcriber CLI version drift | Add version check in mixin, documented minimum version in README |
| Streaming output parsing breaks | Fallback to file-based output mode; log warning |
| No Python fallback if transcriber fails | Subprocess wraps transcriber with timeout; raise detailed `TranscriberError` with CLI stderr |
| User loses old whisper-based workflow | Document migration path: transcriber CLI models are the same whisper.cpp models, quality identical |
| Initial prompt (Chinese commercial phrases) removed from default | Preserve as default `TRANSCRIBER_INITIAL_PROMPT` value in config for backward compat |
