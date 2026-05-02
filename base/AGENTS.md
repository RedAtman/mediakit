# BASE KNOWLEDGE BASE

## OVERVIEW
Core class hierarchy for media objects and test infrastructure.

## STRUCTURE
- `media.py` (292L): BaseMedia class. FFmpeg wrapper, metadata, MD5, DB persistence.
- `video.py` (777L): Video class. Inherits BaseMedia + MixinMediaFasterWhisper.
- `audio.py`: BaseAudio class. Uses `utils.command`.
- `folder.py`: BaseFolder class. Stripped-down orchestrator.
- `basetest.py` (349L): BaseTest class. HTTP, auth, AssertWrap metaclass.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| FFmpeg command building | `video.py` | Inline in methods, violates DRY |
| Metadata extraction | `media.py` | Via ffprobe |
| Complex video ops | `video.py:combine()` | 167L hotspot, 4+ nesting levels |
| Video-specific metadata | `video.py` | `frames_count`, `width_height`, `bitrate`, `duration` |
| Test setup | `basetest.py` (349L) | HTTP + auth + AssertWrap |
| Progress monitoring | `media.py` | StdoutProgress, MediaStateProgress |
| File validation | `media.py` | guess(), path check |
| MD5 calculation | `media.py` | via `utils.file.calculate_md5` |
| DB model mapping | `media.py` | Uses `models.Media` |

## CONVENTIONS
- FFmpeg commands built as lists for `subprocess`.
- `BaseMedia._LOCK` used for thread safety.
- `Video` methods often use `_run_command` from parent.
- `Video` inherits from `BaseMedia` and `MixinMediaFasterWhisper`.
- `BaseMedia` raises `NotMediaException` for invalid files.
- `BaseMedia` uses `Path(path).absolute().as_posix()` for consistency.

## ANTI-PATTERNS
- Inline FFmpeg command building in `video.py` (violates DRY).
- Mixing HTTP/Auth concerns in `basetest.py`.
- `BaseMedia` handles too many concerns (validation, metadata, DB, progress).
- `video.py` has 4+ nesting levels in `combine()`.
- `BaseMedia` has side effects in `__init__` (DB `get_or_create`).
