## ADDED Requirements

### Requirement: Unused modules are removed
Modules with zero production imports SHALL be deleted from the codebase.

#### Scenario: handler.py deletion
- **WHEN** `grep -r 'handler' src/ base/ folder.py cli --include='*.py'` excluding utils/handler.py itself
- **THEN** if zero references found, `utils/handler.py` SHALL be deleted

#### Scenario: baidu_translate.py deletion
- **WHEN** `grep -r 'baidu_translate\|BaiduTranslator' src/ base/ folder.py cli --include='*.py'`
- **THEN** if zero references found, `utils/baidu_translate.py` SHALL be deleted

#### Scenario: speech.py deletion
- **WHEN** `grep -r 'speech\|VoiceAssistant' src/ base/ folder.py cli --include='*.py'`
- **THEN** if zero references found, `utils/speech.py` SHALL be deleted

#### Scenario: metaclass.py deletion
- **WHEN** `grep -r 'metaclass\|Singleton' src/ base/ folder.py cli --include='*.py'`
- **THEN** if zero references found, `utils/metaclass.py` SHALL be deleted

### Requirement: Unused classes and functions are removed
Classes and functions with zero production imports or calls SHALL be removed.

#### Scenario: BoundedExecutor removal from executor.py
- **WHEN** `grep -r 'BoundedExecutor' src/ base/ folder.py cli --include='*.py'`
- **THEN** if zero references found, `BoundedExecutor` class and its `__all__` entry SHALL be removed from `utils/executor.py`

#### Scenario: Unused decorators removed
- **WHEN** `grep -r 'decorator\.singleton\|decorator\.exception\|decorator\.class_property' src/ base/ folder.py cli --include='*.py'`
- **THEN** unused decorator functions and their `__all__` entries SHALL be removed from `utils/decorator.py`

#### Scenario: Unused tools functions removed
- **WHEN** `grep -r 'loading_bar\|progressbar' src/ base/ folder.py cli --include='*.py'`
- **THEN** unused functions and their `__all__` entries SHALL be removed from `utils/tools.py`

#### Scenario: Unused file utility functions removed
- **WHEN** `grep -r 'change_file_extension\|soft_remove' src/ base/ folder.py cli --include='*.py'`
- **THEN** unused functions SHALL be removed from `utils/file.py`
