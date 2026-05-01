# SRC KNOWLEDGE BASE

## OVERVIEW
Core logic package containing models, mixins, and the MiddlewareScheduler pattern for media operations.

## STRUCTURE
```
src/
├── models/      # Data definitions (SQLAlchemy + SQLModel)
├── mixins/      # Functional extensions for Folder and Media classes
├── patterns/    # Architectural building blocks (Middleware)
├── schedulers/  # CLI action dispatchers and task runners
├── file/        # File system monitoring and operations
├── db.py        # DatabaseEngine singleton
├── schemas.py   # Pydantic models and State enums
└── signals.py   # SQLAlchemy event listeners
```

## WHERE TO LOOK
| Component | File | Notes |
|-----------|------|-------|
| Media Model | `models/media.py` (169L) | Primary SQLAlchemy declarative model |
| Legacy Model | `models/_media.py` (105L) | SQLModel version, migration in progress |
| DB Mixins | `mixins/db.py` (205L) | Convergence hub for Folder batch operations |
| Transcription | `mixins/whispers.py` (199L) | Whisper AI integration logic |
| Middleware | `patterns/middleware_context_closure.py` (173L) | Core scheduler execution pattern |
| Folder Actions | `schedulers/folder.py` (182L) | Dispatchers for compress, scale, trim, etc. |
| State Enums | `schemas.py` | StateChoices: -2 failed, -1 unprocessed, 2 finished |
| DB Engine | `db.py` | Singleton with cached engine and session factory |
| Watcher | `file/watcher.py` | File system event handling logic |

## CONVENTIONS
- **Signals**: Registered via side effect imports in `src/__init__.py`.
- **Models**: Prefer SQLAlchemy for new features. SQLModel is being phased out.
- **Mixins**: Use for cross-cutting concerns (DB persistence, AI features).
- **Schedulers**: Every CLI action must be a `MiddlewareScheduler` instance.

## ANTI-PATTERNS
- **Infinite Loops**: Never call `ctx.next()` inside core functions in `patterns/`.
- **Circular Imports**: Avoid importing `src/` subpackages from `utils/`.
- **Direct DB Access**: Use `DatabaseEngine` from `db.py` instead of manual engine creation.
- **State Hardcoding**: Use `StateChoices` from `schemas.py` for all media status checks.
