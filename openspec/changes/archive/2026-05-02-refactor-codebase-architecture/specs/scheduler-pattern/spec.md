## ADDED Requirements

### Requirement: Trivial schedulers use direct function dispatch
MiddlewareScheduler instances with a single middleware and identity core SHALL be replaced with direct function calls.

#### Scenario: _config-only compress scheduler
- **WHEN** the compress action is dispatched
- **THEN** the `_config` middleware SHALL run on kwargs
- **THEN** the compress Folder method SHALL be called directly (no MiddlewareScheduler wrapper)

#### Scenario: _config-only convert scheduler
- **WHEN** the convert action is dispatched
- **THEN** the `_config` middleware SHALL run on kwargs
- **THEN** the convert Folder method SHALL be called directly

#### Scenario: _config-only trim scheduler
- **WHEN** the trim action is dispatched
- **THEN** the `_config` middleware SHALL run on kwargs
- **THEN** the trim Folder method SHALL be called directly

#### Scenario: _config-only combine scheduler
- **WHEN** the combine action is dispatched
- **THEN** the `_config` middleware SHALL run on kwargs
- **THEN** the combine Folder method SHALL be called directly

### Requirement: Middleware context enforces next() call
The Context object SHALL detect whether `ctx.next()` was called during middleware execution and raise if core was skipped.

#### Scenario: Middleware chain terminates without ctx.next()
- **WHEN** a middleware function returns without calling `ctx.next()`
- **THEN** the Context SHALL detect the missing call
- **THEN** an explicit error SHALL be raised indicating chain termination without next()

#### Scenario: Normal middleware chain with ctx.next()
- **WHEN** each middleware calls `ctx.next()`
- **THEN** the chain SHALL execute normally
- **THEN** no enforcement error SHALL be raised

### Requirement: Scheduler pattern is tested
The middleware loading, wrapping, and execution contract SHALL have test coverage.

#### Scenario: _load_middleware resolves config-imported middlewares
- **WHEN** `_load_middleware()` is called with a list of middleware class path strings
- **THEN** it SHALL return callable middleware instances
- **THEN** invalid paths SHALL raise ImportError

#### Scenario: _wrap creates chain with ctx contract
- **WHEN** `_wrap()` creates the middleware chain
- **THEN** the chain SHALL pass kwargs through each middleware in order
- **THEN** each middleware SHALL receive the Context object
