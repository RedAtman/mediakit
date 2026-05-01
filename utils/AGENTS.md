# UTILS KNOWLEDGE BASE

## OVERVIEW
Shared utility layer providing subprocess management, media categorization, logging, and database abstractions.

## STRUCTURE
utils/
├── db/           # Database abstraction layer (SQLAlchemy, SQLite, SQLModel)
├── logger/       # Logging configuration, formatters, and filters
├── process/      # FFmpeg output parsing for progress tracking
├── command.py    # CommandExecutor for ffmpeg subprocess management (145L)
├── media.py      # Media categorization via extension/mime mapping (472L)
├── executor.py   # TaskManager with parallel execution (200L)
├── response.py   # Shared response models (154L)
├── progress.py   # Progress tracking with layer violation (195L)
└── speech.py     # Speech recognition utilities (153L)

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| FFmpeg execution | `utils/command.py` | Subprocess management with cpulimit support |
| Media types | `utils/media.py` | 300+ extension mapping if-elif chain |
| Parallel tasks | `utils/executor.py` | Multi-threaded TaskManager |
| Logging init | `utils/logger/init.py` | dictConfig setup (223L) |
| DB Engines | `utils/db/` | Abstractions for SQLite, SQLAlchemy, and SQLModel |
| CLI Parsing | `utils/cli.py` | Argument parser factory |
| Video Parsing | `utils/video.py` | Resolution and metadata parsing (119L) |
| Decorators | `utils/decorator.py` | Uses command and response utilities (151L) |

## CONVENTIONS
- **Dependency Flow**: base/ -> utils/ (no reverse allowed)
- **Subprocess**: Always use `CommandExecutor` for ffmpeg calls
- **Logging**: Use custom filters from `utils/logger/filters.py` (142L)
- **Responses**: Use `utils.response.Response` for consistent return types

## ANTI-PATTERNS
- **Layer Violation**: `utils/progress.py` imports `src.models` at module bottom—do NOT replicate.
- **Direct Subprocess**: Avoid `subprocess.run` directly; use `utils.command`.
- **Circular Imports**: Do not import from `base/` or `src/` (except the `progress.py` exception).
