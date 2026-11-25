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
├── src/          # Core package: models, mixins, patterns, schedulers, config_file.py (watch TOML)
├── utils/        # Shared utilities: command, db, logger, process, media
│   ├── throttle/ # CPU throttling subsystem (coordinator, throttler, sampling)
│   └── media_types.json  # Extension→category mapping (data-driven)
├── tests/        # pytest suite (flat, 30 files)
├── cli.py          # Entry point (shebang + [project.scripts] → mediakit)
├── folder.py       # Root-level Folder orchestrator (MRO: BaseFolder + SqlAlchemyFolderMixin)
├── config.py       # Environment config with side-effect imports (sys.path, logging init, find_dotenv)
└── pyproject.toml  # uv + pytest + Ruff + pyright + tqdm
```

## WHERE TO LOOK

| Task                      | Location                                     | Notes                                                                                                            |
| ------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| CLI entry                 | `cli.py`                                     | Entry point (`mediakit` via `[project.scripts]`), parser from `utils.cli`, dispatch to `src.schedulers.folder.*` |
| Media operations          | `base/video.py` (558L), `base/audio.py`      | FFmpeg wrapper methods                                                                                           |
| Folder batch ops          | `folder.py` + `base/folder.py`               | `Folder` class with DB mixin                                                                                     |
| DB models                 | `src/models/media.py`                        | SQLAlchemy model (single source)                                                                                 |
| State machine             | `src/schemas.py`                             | Pydantic State model (-3 ignored → -2 failed → 2 finished)                                                       |
| DB engine                 | `src/db.py`                                  | Injectable engine via `get_engine(engine=None)`                                                                  |
| Scheduler dispatcher      | `src/schedulers/folder.py`                   | MiddlewareScheduler (compress) + _SimpleScheduler (trivial actions, stop)                                        |
| Watcher scheduler         | `src/schedulers/watcher.py` (514L)           | Watch mode: Observer + DebounceBuffer + FileStabilityTracker + callbacks.mark_compress_outcome                  |
| Dedupe                    | `src/schedulers/dedupe.py`                   | md5-based dedup: scans watched folders, moves duplicate media copies to macOS Trash (dry-run by default)          |
| Middleware pattern        | `src/patterns/middleware_context_closure.py` | Runtime ctx.next() enforcement; raises RuntimeError if middleware returns without calling it                     |
| Config                    | `config.py`                                  | Environment subclass pattern (Development/Testing/Production)                                                    |
| Watch config (TOML)       | `src/config_file.py`                         | `~/.config/mediakit/config.toml`: folders, per-path overrides, longest-prefix `Resolver`, pydantic fail-fast       |
| CPU throttler coordinator | `utils/throttle/coordinator.py` (241L)       | `CPULimiterCoordinator` manages per-PID `ProcessThrottler` instances, manual override/distribution               |
| CPU throttler process     | `utils/throttle/throttler.py` (154L)         | `ProcessThrottler` daemon thread: samples CPU, SIGSTOP/SIGCONT via duty cycle controller                         |
| CPU sampling              | `utils/throttle/sampling.py` (233L)          | macOS: `ps` primary, `proc_pidinfo` ctypes fallback. Linux: `/proc/stat`                                         |
| Media type registry       | `utils/media_types.json`                     | Data-driven extension→category mapping loaded by `utils/media.py`                                                |
| Logging setup             | `utils/logger/init.py`                       | dictConfig with custom filters                                                                                   |
| Progress bars             | `utils/progress.py`                          | tqdm (stdout TTY / stderr non-TTY) + MediaStateProgress (DB)                                                     |
| Translation               | `utils/translator.py`                        | Baidu Translate API; lazy config validation (`_require_config()` at runtime, not import)                         |

## CONVENTIONS

- **Line length**: 120 chars (Ruff)
- **Quotes**: Single quotes (Ruff format)
- **String normalization**: Off (Ruff `format.skip-magic-trailing-comma`)
- **Imports**: Ruff import sorting (I rule), 5-group order, forced alphabetical within sections
- **Types**: pyright `basic` mode (not strict)
- **Lint pipeline**: vulture (100%) → codespell → ruff
- **Lint/format gate**: `pre-commit` (`.pre-commit-config.yaml` → ruff check F401/F841/I + ruff format) is the
  commit gate; codespell and vulture are dev dependencies run by hand. There is no `scripts/` directory
- **CLI dispatch**: MiddlewareScheduler pattern (not argparse subcommands)
- **Config**: `from config import CONFIG` — all env vars via subclass attributes
- **Testing**: pytest with unittest.TestCase, mock.patch, setUp pattern
- **Dead code**: Vulture at 100% min-confidence — no false positives tolerated
- **Lint tools**: `ruff`, `codespell`, `vulture` installed as dev deps
- **Commit**: the installed pre-commit hook formats staged files with ruff and aborts the commit if it changed
  anything (re-stage and commit again)

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT reintroduce shell launchers for the daemon** — `watcher.sh` / `watcher_.sh` / `var/folder.sh` were removed: watch config now lives in `~/.config/mediakit/config.toml`, single-instance protection is in `WatcherScheduler._ensure_single_instance()`, logging is rotated by the app and launchd owns the process lifecycle

- **Do NOT call ctx.next() inside core functions** — causes infinite loop in MiddlewareScheduler
- **Do NOT import src/ from utils/** — `utils/progress.py` imports `src.models` which creates fragile layer coupling
- **Do NOT extend config.py import graph** — already has side effects (sys.path insert, logging init)
- **Do NOT collapse the watch list to ancestor roots** — each configured folder is an independent unit of identity: `_path_to_watch` maps one watch per configured path, config reload diffs `to_add`/`to_remove` per path and `unschedule`s exactly the removed one, and `_feed_existing(path)` builds one `Folder(path)` per configured dir. Watching a common ancestor recursively (e.g. two roots for a 224-entry list) would delete 100+ watches from one config line change and would start processing subdirectories nobody configured. `collapse_nested` is therefore applied only when `recursive=True`, where a parent genuinely covers its children
- **Do NOT put config validation at class body** — `utils/translator.py` originally raised ValueError at import time; use `@classmethod _require_config()` called at runtime instead

## UNIQUE STYLES

- **MiddlewareScheduler**: Pre-configured middleware chains instead of argparse subcommands. Each action (compress, scale, etc.) is a `MiddlewareScheduler` instance in `src/schedulers/folder.py`
- **Single SQLAlchemy model**: `src/models/media.py` is the only ORM model (`utils/db/_sqlalchemy.py` engine); the old SQLModel `_media.py` was removed
- **Class-level thread lock**: `BaseMedia._LOCK = threading.Lock()` — shared across all instances
- **Static method triples**: `run_()` / `run__()` / `run___()` for batch dispatch
- **Lazy config validation**: `utils/translator.py` defers Baidu Translate credential checks to `_require_config()` called inside `translate()` — avoids import-time crashes when env vars are missing
- **Progress bar: tqdm with TTY detection**: `TqdmProgress` in `utils/progress.py` auto-detects TTY: uses `sys.stdout` + `dynamic_ncols` for interactive terminals, `sys.stderr` + `ascii=True` for daemon/watch mode (non-TTY, log-friendly)
- **FFmpeg progress pipe**: `base/video.py` passes `-progress pipe:1 -nostats` to ffmpeg — sends machine-readable progress to stdout (unbuffered), parsed by `FfmpegCurrentFrameStdoutParser` in `utils/process/parser.py`
- **Callback failure handling**: `src/schedulers/callbacks.py::mark_compress_outcome` is the ONLY place that turns a finished compress task into DB state — `result == 0` sets `StateChoices.finished(2)` + `soft_remove`, `ResultStatus.NOT_MEDIA(602)` sets `StateChoices.ignored(-3)` (file left where it is), otherwise `StateChoices.failed(-2)`. Both `_callback` (folder) and `_batch_callback` (watcher) call it and keep only their own bookkeeping; do not re-implement the state decision in either
- **"Not media" is decided by content, not by extension**: `BaseMedia.get_metadata` raises `exceptions.NotMediaException(101)` when ffprobe cannot open the file (e.g. AppleDouble `._foo.mp4`, which borrows a real video extension). `utils/decorator.exception` turns that into `ResultStatus.NOT_MEDIA(602)`, the watcher probes `media.metadata` before scheduling a task (the cached probe is reused by compress, so no extra process), and `ignored` is terminal: `QUERY_UNPROCESSED` only re-queries `unprocessed`/`failed`. Extension matching (`reject_reason`, the watcher `dispatch` gate) is a cheap prefilter only — never the authority. Recovery has two distinct branches: **content changed** (a finished download) means a new md5, hence a new row that is queued normally — the stale `-3` row is left behind as an orphan; **same bytes, only readable again** (permissions, remount) keeps the row at `-3`, so scans never retry it and only a fresh watch event can, because a task's opening `update_state` writes `unprocessed` back. `os.access` only inspects permission bits, so an SMB/cloud hiccup that fails on open but passes `access` still ends at `ignored`
- **Result contract**: the watcher feeds tasks through `media_compress.core` (not `Folder.run__`) precisely so results arrive as `response.Result`; `Folder.run__` returns plain dicts and would silently skip every state update
- **Watcher folder file fallback**: `src/file/paths.py::find_folder_file()` resolves the folder list via: (1) `WATCH_FOLDER_FILE` env var (missing file logs a warning instead of being skipped silently), (2) `~/.config/mediakit/folders.txt`, (3) parent-dir walk from cwd for the legacy `var/folder.sh`, (4) the same walk from config.py's location. `parse_folder_file()` (expanduser + normpath + de-dup) and `collapse_nested()` live in the same module so watcher and dedupe share one parser

## WATCHER INVARIANTS

Watch mode is the only long-lived process in the project, so these values are observable
behaviour rather than tuning knobs — changing one changes what a user sees. They used to
live only in a 975-line implementation plan; keep them here instead.

| Knob | Value | Observable consequence |
| --- | --- | --- |
| `DebounceBuffer(calm_period=)` | 5.0 s | a burst of writes is flushed once, 5 s after the last event |
| `DebounceBuffer(max_flush_interval=)` | 60.0 s | a file that never stops being written is still flushed after 60 s |
| `FileStabilityTracker(sample_interval=, stable_samples=, timeout=)` | 1.0 s / 3 / 30 s | a file is processed only after size+mtime stop changing for 3 samples; it is given up on after 30 s |
| config mtime poll | 5.0 s | editing the folder file adds/removes watched dirs without a restart |
| pid file | `~/.mediakit/daemon.pid` | written on start, removed on graceful exit, read by `mediakit stop` |
| FSEvents emitter | one per watched path: ~33 KB (thread stack) plus one kernel stream | 224 paths ≈ 8 MB, 227 threads, ~2100 fds — measured, not estimated. Scheduling costs ~95 ms per stream and cannot be parallelised (macOS serialises stream creation): 224 paths ≈ 23 s before the daemon is fully watching. De-dupe/normalize the list (`src/file/paths.py`); treat a 4-digit path count as a bug |

## COMMANDS

```bash
# Fix lint issues
uv run ruff check --fix . tests

# Install pre-commit hook (one-time setup)
pre-commit install

# Run full lint pipeline (manual)
pre-commit run --all-files

# Test
pytest -vv --rootdir . --color=yes --capture=tee-sys

# Lint
uv run ruff check . tests

# Build sdist + wheel
uv build

# Build the frozen binary (see NOTES for what the spec carries)
uv run --with pyinstaller==6.22.3 pyinstaller mediakit.spec --distpath dist --workpath build

# Format
uv run ruff format .

# Print version (single source: pyproject.toml [project].version)
mediakit -v

# Run CLI (compress)
mediakit compress -t video -w 1 -f /path/to/folder

# Run CLI with CPU throttling (-c = CPU limit %)
mediakit compress -t video -w 1 -c 50 -f /path/to/folder

# Compress output resolution / fps (default fallback: COMPRESS_RESOLUTION=HD, COMPRESS_FPS=24)
# --resolution takes an enum name (HD/FHD/WQHD/UHD...) or WxH, case-insensitive; downscale only
mediakit compress -t video -f /path/to/folder --resolution FHD --fps 30

# Watch mode (auto-process new files)
mediakit compress -t video --watch -f /path/to/folder

# Watch mode with folder file
mediakit compress -t video --watch   # 读 ~/.config/mediakit/config.toml

# Stop running watch daemon (graceful)
mediakit stop

# Force stop watch daemon (SIGKILL to process group)
mediakit stop --force

# Dedupe: find media files with identical md5, move duplicates to Trash
# (dry-run by default; --apply performs the actual removal)
mediakit dedupe [--apply]

# Watcher (macOS LaunchAgent)
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/mediakit.plist
```

## COMMIT RULES

- **Do NOT commit `docs/`** — All files under `docs/` are excluded from commits
- **Archive openspec before committing** — `openspec/changes/<name>` must be archived to `openspec/changes/archive/` before any openspec files can be committed

## RELEASING

`.github/workflows/ci.yml` runs the pre-commit hooks plus the pytest suite on
ubuntu-latest and macos-latest for pushes/PRs to `main` and `dev`.
`.github/workflows/release.yml` fires on any `v*` tag, re-runs the suite, refuses
to publish unless the tag equals `[project].version` in `pyproject.toml`, then
builds sdist+wheel and attaches them to a GitHub release
(`alpha`/`beta`/`rc` in the tag marks it prerelease).

```bash
# cut a release
# 1. bump [project].version in pyproject.toml (the only version source; `mediakit -v` reads it)
# 2. commit, then tag the exact commit
git tag v0.1.1 && git push origin v0.1.1
```

No secrets required: the release uses the default `GITHUB_TOKEN` with
`contents: write`.

- **0.1.7 widened `State`'s lower bound to `-3` (ignored)** — a binary older than
  0.1.7 will hit a pydantic `ValidationError` if it ever deserialises a row written by
  0.1.7+. Old versions only query `-1/-2`, so the exposure is limited to paths that
  `update_state` every row; back up `db.db` before any downgrade comparison.

## NOTES

- **Frozen binary** — `mediakit.spec` is the single source of truth for packaging:
  `uv run --with pyinstaller==6.22.3 pyinstaller mediakit.spec --distpath dist --workpath build`. CI runs
  exactly that in the `binary` job of `.github/workflows/release.yml` for macOS arm64/x86_64, Linux
  x86_64 and Windows, and attaches `mediakit-<os>-<arch>` to the GitHub release. ffmpeg is **not**
  bundled: the binary shells out to a system ffmpeg on PATH, same as the pip/uv install
- **Frozen paths** — onefile puts `__file__` in a temp dir that is deleted on exit, so `config.py`
  anchors `BASE_DIR` to `sys.executable` when `sys.frozen` is set (that is only the import root).
  `STATE_DIR` — and therefore `db.db` and `logs/` — comes from `frozen_state_dir()`: `~/Library/
  Application Support/mediakit` on macOS, `~/.local/state/mediakit` on Linux, `%LOCALAPPDATA%\mediakit`
  on Windows, precisely so `brew upgrade` cannot delete the database. A `.env` (or `~/.env`) that sets
  `SQLITE_DATABASE` still overrides this
- **Frozen bundle needs explicit hidden imports for every dynamic import** — `src/__init__.py`
  (`src.signals`), `config.py` (`utils.logger.init`, plus the `dictConfig` `()` entries that
  reflect `utils.logger.filters/formatters`), and `folder.py` (`base.{video,audio}` chosen from the
  `--type` flag). Static analysis cannot see any of them
- **`multiprocessing` is excluded from the bundle on purpose** — nothing here uses processes
  (`utils/executor.py` is ThreadPoolExecutor-only and borrows `os.cpu_count()`), but the module still
  gets bundled: PyInstaller's multiprocessing runtime hook then spawns a helper that re-enters this
  very frozen CLI, so argparse reads the hook's `-c` payload as `--cpu-limit` and the resource_tracker
  dies (older failure path: `No module named 'array'` in the onefile child). Verified 2026-11-23 by
  removing the exclude: the encode still finished, but every run printed the argparse error plus a
  `process died unexpectedly` warning. `ffmpeg-python -> future.moves` used to be one importer of the
  module; dropping that dependency (it was only used by a single `ffmpeg.probe` call, now gone) did
  **not** make the module unreachable, so the exclude has to stay
- **LaunchAgent gotchas (learned the hard way)** — (1) launchd does not inherit the login shell's PATH
  (`/usr/bin:/bin` only), so with an empty `FFMPEG_BIN_DIR` the daemon starts and then fails every task with
  "No such file or directory: 'ffprobe'"; the plist ships `EnvironmentVariables.PATH`. (2) A plist copied out of
  Dropbox carries `com.apple.quarantine`/`com.dropbox.attrs`, and `launchctl bootstrap` then fails with a bare
  `5: Input/output error` while `plutil -lint` passes — run `xattr -c` on the installed copy. (3) `KeepAlive`
  uses `SuccessfulExit: false` so `mediakit stop` (SIGTERM, exit 0) leaves the job down, while the
  single-instance guard exits 1 on purpose — launchd then retries it every `ThrottleInterval`, which is the
  behaviour we want when a stray daemon holds the pid file
- **CPU throttling degrades instead of crashing off Linux/macOS** — `utils/throttle/sampling.py`
  only implements those two, so `CPULimiterCoordinator` checks the platform up front and runs
  unthrottled with one warning. This is what keeps the Windows binary usable

- `.venv/` has 22k+ files from dependencies — excluded from AGENTS.md analysis
- **`requires-python` is `>=3.14,<3.15` on purpose** — pyobjc 11.1 has no cp315 wheel, so building `pyobjc-framework-quartz` from source fails on 3.15 and takes the whole `uv sync` down with it. Without the upper bound uv auto-selects the newest homebrew `python3` (3.15) whenever `.venv` is missing or deemed stale. Remove the bound only after confirming pyobjc ships cp315 wheels
- **`uv lock` is safe now** — the lock is already at revision 5 and the local uv (0.13.7) regenerates
  it without the old platform-marker churn: dropping `ffmpeg-python`/`future` produced a 24-line
  deletion with no unrelated changes (verified 2026-11-23). The old advice to hand-edit a single line
  applied to the revision 3 → 5 bump and is stale; still run `uv lock --check` after hand edits
- **`[database] path` is applied in `cli.main`, before any scheduler** — `DatabaseEngine.engine()` is a cached
  lazy property, so `apply_database_path()` sets `CONFIG.SQLITE_DATABASE`, calls `DatabaseEngine.reset()` and
  creates the parent dir; the engine itself still creates the file on first use. Precedence is `SQLITE_DATABASE`
  env > config file > default (a conflicting env logs a warning, since the user's `.env` silently winning is the
  trap we already hit with `WATCH_FOLDER_FILE`). `stop` deliberately skips config loading so a broken config can
  never block stopping a daemon. `dedupe` defaults to `CONFIG.SQLITE_DATABASE` and `--db` overrides it
- **The starter config has one source** — `src/config_file.py::EXAMPLE_CONFIG_TEXT` is what `mediakit
  --init-config` writes (refusing to overwrite); the repo's `config.toml.example` must stay byte-identical and a
  test enforces it, otherwise the example rots. `folders.txt.example` is validated through `parse_folder_file`
  the same way. A run with no configured folders is a hard failure (`nothing to watch …`), never a silent watch
  of `MEDIA_FILE_FOLDER`
- **CLI flags beat the config file for compress params** — `Resolver.compress_opts_for()` layers
  `[compress]` then the matched `[[watch.folders]].compress`, then overwrites with whatever CLI passed
  (`resolution`/`fps` that were actually given). An explicit `--resolution` therefore always wins, which is
  what the README promises
- **Watch config lives in `~/.config/mediakit/config.toml` (XDG, even on macOS), state stays in the platform
  state dir** — config vs state is the split; `logs/`/`db.db` do not move. Discovery order: `--config` →
  `MEDIAKIT_CONFIG` → `~/.config/mediakit/config.toml`; with no TOML it falls back to `--folder-file` →
  `~/.config/mediakit/folders.txt` → legacy `var/folder.sh` walk-ups → `-f DIR`. A bad key/path/resolution
  aborts startup via `ConfigError` (cli prints one line), because a silently-ignored typo is worse than refusing to
  start. `[watch] folders_file` keeps a plain one-path-per-line list usable, so 300+ entries need not be rewritten;
  `[[watch.folders]]` entries are merged on top and win on duplicates. Per-path `media_type`/`recursive`/`compress`
  are resolved by longest prefix over the event path (`Resolver`, realpath on both sides because macOS `/tmp` is
  `/private/tmp`); watch keeps ONE buffer/handler, so per-path behaviour must stay a lookup, not per-path threads.
  Editing the file hot-reloads folders and resolution/fps; `recursive` changes need a restart. `cpu_limit` is
  global by design (single coordinator) and `max_workers` stays global for now (one pool per flush batch)
- `build/` directory contains stale frozen distribution (bdist.macosx-15.0-arm64)
- Largest complexity hotspot: `base/video.py:combine()` — 167 lines, 4+ nesting levels
- `config.py` uses `find_dotenv(usecwd=True)` to load `.env` — falls back to `~/.env` if not found in cwd
- `FFMPEG_BIN_DIR` default is `/opt/homebrew/bin` (not the `ffmpeg` binary) — `os.path.join()` appends `ffmpeg`
- The folder list defaults to `~/.config/mediakit/folders.txt` (`CONFIG.WATCH_FOLDER_FILE` was removed: `src/file/paths.py` reads the `WATCH_FOLDER_FILE` env var directly); the legacy `var/folder.sh` keeps working as a last-resort fallback, and an env var pointing at a missing file now logs a warning instead of being skipped silently
- `utils/translator.py` must NOT validate config at class body level — import-time crash when env vars missing
- `_batch_callback` receives `response.Result` objects (not plain dicts) — always use `result.data.get("media")`, never `result.get("new_file_path")`
- `base/video.py` compress command includes `-progress pipe:1 -nostats` — ffmpeg outputs machine-readable progress to stdout (unbuffered)
- **`media.title` must never include the extension** — `Media.path` is `dirname/title.ext`, so a title ending in `.mp4` produced `x.mp4.mp4`. A one-off migration stripped the extension from 242 stale rows on 2026-11-25; **do not re-run that UPDATE** — a file legitimately named `movie.mp4.mp4` (title `movie.mp4`, ext `mp4`) would be stripped a second time and lose its real name
