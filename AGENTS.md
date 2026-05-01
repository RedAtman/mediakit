# PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-01
**Commit:** c04e7fd
**Branch:** dev

## OVERVIEW

media_handler — Python 3.12+ CLI tool for batch media operations (compress, convert, scale, trim). Uses ffmpeg via subprocess with cpulimit, SQLAlchemy for state tracking, and middleware-scheduler pattern for CLI dispatch.

## STRUCTURE

```
media_handler/
├── base/         # Base class hierarchy (Media → Audio/Video/Image)
├── src/          # Core package: models, mixins, patterns, schedulers
├── utils/        # Shared utilities: command, db, logger, process, media
├── tests/        # pytest suite (flat, 15 files)
├── cli           # Entry point (no .py extension, executable)
├── folder.py     # Root-level Folder orchestrator (MRO: BaseFolder + SqlAlchemyFolderMixin)
├── config.py     # Environment config with side-effect imports (sys.path, logging init)
├── watcher.sh    # macOS LaunchAgent watcher loop
└── pyproject.toml # PDM + pytest + Black + Ruff + isort + pyright
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI entry | `cli` | Parser from `utils.cli`, dispatch to `src.schedulers.folder.*` |
| Media operations | `base/video.py` (740L), `base/audio.py` | FFmpeg wrapper methods |
| Folder batch ops | `folder.py` + `base/folder.py` | `Folder` class with DB mixin |
| DB models | `src/models/media.py`, `src/models/_media.py` | SQLAlchemy + SQLModel hybrid |
| State machine | `src/schemas.py` | Pydantic State model (-2 failed → 2 finished) |
| DB engine | `src/db.py` | Singleton via `@classmethod @property @cache` |
| Scheduler dispatcher | `src/schedulers/folder.py` | MiddlewareScheduler instances |
| Middleware pattern | `src/patterns/middleware_context_closure.py` | ctx.next() inside core = infinite loop (design constraint) |
| Config | `config.py` | Environment subclass pattern (Development/Testing/Production) |
| Logging setup | `utils/logger/init.py` | dictConfig with custom filters |
| Progress bars | `utils/progress.py` | Stdout + MediaState progress |
| Test base | `base/basetest.py` (349L) | HTTP + auth mixin |

## CONVENTIONS

- **Line length**: 120 chars (Black, isort, Pylint)
- **Quotes**: Single quotes (Ruff format)
- **String normalization**: Off (Black `skip-string-normalization`)
- **Imports**: isort with Black profile, 5-group order, forced alphabetical within sections
- **Types**: pyright `basic` mode (not strict)
- **Lint pipeline**: vulture (100%) → codespell → ruff → isort-check → black-check
- **PDM scripts**: `isort`, `format`, `ruff`, `fix`, `lint`, `codespell`
- **CLI dispatch**: MiddlewareScheduler pattern (not argparse subcommands)
- **Config**: `from config import CONFIG` — all env vars via subclass attributes
- **Testing**: pytest with unittest.TestCase, mock.patch, setUp pattern
- **Dead code**: Vulture at 100% min-confidence — no false positives tolerated

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT call ctx.next() inside core functions** — causes infinite loop in MiddlewareScheduler
- **Do NOT import src/ from utils/** — `utils/progress.py` imports `src.models` which creates fragile layer coupling
- **Do NOT extend config.py import graph** — already has side effects (sys.path insert, logging init)

## UNIQUE STYLES

- **MiddlewareScheduler**: Pre-configured middleware chains instead of argparse subcommands. Each action (compress, scale, etc.) is a `MiddlewareScheduler` instance in `src/schedulers/folder.py`
- **Dual model pattern**: `_media.py` (SQLModel) and `media.py` (SQLAlchemy) coexist — migration in progress
- **Class-level thread lock**: `BaseMedia._LOCK = threading.Lock()` — shared across all instances
- **Static method triples**: `run_()` / `run__()` / `run___()` for batch dispatch

## COMMANDS

```bash
# Test (pytest 8.0.0+)
pytest -vv --rootdir . --color=yes --capture=tee-sys

# Lint
pdm run lint

# Format
pdm run format

# Run CLI
python cli compress -t video -w 1 -f /path/to/folder

# Watcher (macOS LaunchAgent)
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/media_handler.plist
```

## NOTES

- `.venv/` has 22k+ files from dependencies — excluded from AGENTS.md analysis
- Config loads logger at module end via `import_module("utils.logger.init")` — import order matters
- `build/` directory contains stale frozen distribution (bdist.macosx-15.0-arm64)
- Largest complexity hotspot: `base/video.py:combine()` — 167 lines, 4+ nesting levels
