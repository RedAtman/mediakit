## ADDED Requirements

### Requirement: DatabaseEngine supports dependency injection
The `DatabaseEngine.get_engine()` method SHALL accept an optional engine parameter for test injection.

#### Scenario: get_engine() without parameter returns singleton
- **WHEN** `DatabaseEngine.get_engine()` is called without arguments
- **THEN** it SHALL return the cached singleton engine
- **THEN** existing production behavior SHALL be unchanged

#### Scenario: get_engine() with engine parameter returns injected engine
- **WHEN** `DatabaseEngine.get_engine(engine=mock_engine)` is called
- **THEN** it SHALL return the mock_engine directly
- **THEN** the singleton cache SHALL NOT be affected

### Requirement: _media.py is deleted after verification
The legacy `_media.py` SQLModel module SHALL be deleted when confirmed unused.

#### Scenario: Zero production references confirmed
- **WHEN** `grep -r '_media' src/ base/ folder.py cli --include='*.py'` is run
- **WHEN** only test files and the module itself reference it
- **THEN** `src/models/_media.py` SHALL be deleted
- **THEN** `src/models/__init__.py` SHALL be updated to remove _media re-exports

#### Scenario: Test suite passes after deletion
- **WHEN** `_media.py` is deleted
- **WHEN** `pytest -vv` is run
- **THEN** all tests SHALL pass (same count as before deletion)

### Requirement: Layer violation in utils/db/_sqlalchemy.py is fixed
The import `from src import models` SHALL be moved to a late import inside the method that uses it.

#### Scenario: Late import resolves correctly
- **WHEN** `utils/db/_sqlalchemy.py` is loaded
- **THEN** the `src` import SHALL NOT execute at module level
- **WHEN** a method in `_sqlalchemy.py` needs `Base`
- **THEN** the import SHALL execute inside that method body
- **THEN** the behavior SHALL be identical to before
