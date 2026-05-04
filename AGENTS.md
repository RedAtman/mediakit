# PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-04
**Commit:** (HEAD of dev)
**Branch:** dev

## OVERVIEW

mediakit — Python 3.14+ CLI tool for batch media operations (compress, convert, scale, trim, save_text, stop). Uses ffmpeg via subprocess with in-process dynamic CPU throttling (SIGSTOP/SIGCONT), SQLAlchemy for state tracking, middleware-scheduler pattern for CLI dispatch, and tqdm for real-time progress bars.

## STRUCTURE

```
mediakit/
├── base/         # Base class hierarchy (Media → Audio/Video/Image)
├── src/          # Core package: models, mixins, patterns, schedulers
├── utils/        # Shared utilities: command, db, logger, process, media
│   ├── throttle/ # CPU throttling subsystem (coordinator, throttler, sampling)
│   └── media_types.json  # Extension→category mapping (data-driven)
├── tests/        # pytest suite (flat, 17 files)
├── cli.py          # Entry point (shebang + [project.scripts] → mediakit)
├── folder.py       # Root-level Folder orchestrator (MRO: BaseFolder + SqlAlchemyFolderMixin)
├── config.py       # Environment config with side-effect imports (sys.path, logging init, find_dotenv)
├── watcher.sh      # macOS LaunchAgent watcher loop
└── pyproject.toml  # PDM + pytest + Black + Ruff + isort + pyright + tqdm
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI entry | `cli.py` | Entry point (`mediakit` via `[project.scripts]`), parser from `utils.cli`, dispatch to `src.schedulers.folder.*` |
| Media operations | `base/video.py` (777L), `base/audio.py` | FFmpeg wrapper methods |
| Folder batch ops | `folder.py` + `base/folder.py` | `Folder` class with DB mixin |
| DB models | `src/models/media.py` | SQLAlchemy model (single source) |
| State machine | `src/schemas.py` | Pydantic State model (-2 failed → 2 finished) |
| DB engine | `src/db.py` | Injectable engine via `get_engine(engine=None)` |
| Scheduler dispatcher | `src/schedulers/folder.py` | MiddlewareScheduler (compress) + _SimpleScheduler (trivial actions, stop) |
| Watcher scheduler | `src/schedulers/watcher.py` (360L) | Watch mode: Observer + DebounceBuffer + FileStabilityTracker + _batch_callback |
| Middleware pattern | `src/patterns/middleware_context_closure.py` | Runtime ctx.next() enforcement; raises RuntimeError if middleware returns without calling it |
| Config | `config.py` | Environment subclass pattern (Development/Testing/Production) |
| CPU throttler coordinator | `utils/throttle/coordinator.py` (241L) | `CPULimiterCoordinator` manages per-PID `ProcessThrottler` instances, manual override/distribution |
| CPU throttler process | `utils/throttle/throttler.py` (154L) | `ProcessThrottler` daemon thread: samples CPU, SIGSTOP/SIGCONT via duty cycle controller |
| CPU sampling | `utils/throttle/sampling.py` (233L) | macOS: `ps` primary, `proc_pidinfo` ctypes fallback. Linux: `/proc/stat` |
| Media type registry | `utils/media_types.json` | Data-driven extension→category mapping loaded by `utils/media.py` |
| Logging setup | `utils/logger/init.py` | dictConfig with custom filters |
| Progress bars | `utils/progress.py` | tqdm (stdout TTY / stderr non-TTY) + MediaStateProgress (DB) |
| Translation | `utils/translator.py` | Baidu Translate API; lazy config validation (`_require_config()` at runtime, not import) |
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
- **Lint tools**: `ruff`, `codespell`, `vulture` installed as dev deps

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT call ctx.next() inside core functions** — causes infinite loop in MiddlewareScheduler
- **Do NOT import src/ from utils/** — `utils/progress.py` imports `src.models` which creates fragile layer coupling
- **Do NOT extend config.py import graph** — already has side effects (sys.path insert, logging init)
- **Do NOT put config validation at class body** — `utils/translator.py` originally raised ValueError at import time; use `@classmethod _require_config()` called at runtime instead

## UNIQUE STYLES

- **MiddlewareScheduler**: Pre-configured middleware chains instead of argparse subcommands. Each action (compress, scale, etc.) is a `MiddlewareScheduler` instance in `src/schedulers/folder.py`
- **Dual model pattern**: `_media.py` (SQLModel) and `media.py` (SQLAlchemy) coexist — migration in progress
- **Class-level thread lock**: `BaseMedia._LOCK = threading.Lock()` — shared across all instances
- **Static method triples**: `run_()` / `run__()` / `run___()` for batch dispatch
- **Lazy config validation**: `utils/translator.py` defers Baidu Translate credential checks to `_require_config()` called inside `translate()` — avoids import-time crashes when env vars are missing
- **Progress bar: tqdm with TTY detection**: `TqdmProgress` in `utils/progress.py` auto-detects TTY: uses `sys.stdout` + `dynamic_ncols` for interactive terminals, `sys.stderr` + `ascii=True` for daemon/watch mode (non-TTY, log-friendly)
- **FFmpeg progress pipe**: `base/video.py` passes `-progress pipe:1 -nostats` to ffmpeg — sends machine-readable progress to stdout (unbuffered), parsed by `FfmpegCurrentFrameStdoutParser` in `utils/process/parser.py`
- **Callback failure handling**: Both `_callback` (`src/schedulers/folder.py`) and `_batch_callback` (`src/schedulers/watcher.py`) check `result.data.get("media")` and `result == 0` against `response.Result` objects — success sets `StateChoices.finished(2)`, failure sets `StateChoices.failed(-2)`
- **Watcher folder file fallback**: `_find_watch_folder_file()` in `src/schedulers/watcher.py` resolves `var/folder.sh` via: (1) `WATCH_FOLDER_FILE` env var, (2) parent-dir walk from cwd, (3) parent-dir walk from config.py source location

## COMMANDS

```bash
# Test (pytest 8.0.0+)
pytest -vv --rootdir . --color=yes --capture=tee-sys

# Lint
pdm run lint

# Format
pdm run format

# Run CLI (compress)
mediakit compress -t video -w 1 -f /path/to/folder

# Run CLI with CPU throttling (-c = CPU limit %)
mediakit compress -t video -w 1 -c 50 -f /path/to/folder

# Watch mode (auto-process new files)
mediakit compress -t video --watch -f /path/to/folder

# Watch mode with folder file
mediakit compress -t video --watch --folder-file var/folder.sh

# Stop running watch daemon (graceful)
mediakit stop

# Force stop watch daemon (SIGKILL to process group)
mediakit stop --force

# Watcher (macOS LaunchAgent)
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/mediakit.plist
```

## COMMIT RULES

- **Do NOT commit `docs/`** — All files under `docs/` are excluded from commits
- **Archive openspec before committing** — `openspec/changes/<name>` must be archived to `openspec/changes/archive/` before any openspec files can be committed

## NOTES

- `.venv/` has 22k+ files from dependencies — excluded from AGENTS.md analysis
- Config loads logger at module end via `import_module("utils.logger.init")` — import order matters
- `build/` directory contains stale frozen distribution (bdist.macosx-15.0-arm64)
- Largest complexity hotspot: `base/video.py:combine()` — 167 lines, 4+ nesting levels
- `config.py` uses `find_dotenv(usecwd=True)` to load `.env` — falls back to `~/.env` if not found in cwd
- `FFMPEG_BIN_DIR` default is `/opt/homebrew/bin` (not the `ffmpeg` binary) — `os.path.join()` appends `ffmpeg`
- `WATCH_FOLDER_FILE` default is `var/folder.sh` (relative) — resolved at runtime by `_find_watch_folder_file()`
- `utils/translator.py` must NOT validate config at class body level — import-time crash when env vars missing
- `_batch_callback` receives `response.Result` objects (not plain dicts) — always use `result.data.get("media")`, never `result.get("new_file_path")`
- `base/video.py` compress command includes `-progress pipe:1 -nostats` — ffmpeg outputs machine-readable progress to stdout (unbuffered)
