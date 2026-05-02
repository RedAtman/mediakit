## ADDED Requirements

### Requirement: Extension-to-type mapping is data-driven
The inline if-elif chain in `utils/media.py` SHALL be replaced with a JSON data file lookup.

#### Scenario: JSON file loaded successfully
- **WHEN** `utils/media.py` is imported
- **WHEN** the `media_types.json` data file exists and is valid
- **THEN** the extension mapping SHALL be loaded from the JSON file
- **THEN** the lookup behavior SHALL be identical to the if-elif chain

#### Scenario: JSON file missing, falls back to hardcoded dict
- **WHEN** `utils/media.py` is imported
- **WHEN** the `media_types.json` data file does NOT exist or fails to load
- **THEN** the extension mapping SHALL fall back to the existing hardcoded dict
- **THEN** a warning SHALL be logged

#### Scenario: All existing extensions return correct types
- **WHEN** any extension from the original if-elif chain is looked up
- **THEN** the returned media type SHALL be identical to the original mapping

#### Scenario: Unknown extension returns None
- **WHEN** an extension not in the mapping is looked up
- **THEN** `None` SHALL be returned
- **THEN** behavior SHALL be identical to the current implementation
