"""`mediakit --check-config`: 只读体检, 不改任何状态."""

from unittest import mock

from src.config_check import EST_FDS_PER_STREAM, EST_MS_PER_STREAM, build_report
from src.config_file import Settings


def _settings(entries):
    return Settings(watch={'folders': [{'path': p} for p in entries]})


def test_counts_usable_and_missing(tmp_path):
    alive = tmp_path / 'alive'
    alive.mkdir()
    gone = tmp_path / 'gone'

    report = build_report(_settings([str(alive), str(gone)]), str(tmp_path / 'config.toml'))

    assert 'entries  : 2 (after de-duplication)' in report
    assert 'usable   : 1' in report
    assert 'missing  : 1' in report
    assert f'- {gone}' in report


def test_reports_duplicates_and_collapses_them(tmp_path):
    alive = tmp_path / 'alive'
    alive.mkdir()
    report = build_report(_settings([str(alive), str(alive)]), str(tmp_path / 'c.toml'))
    assert 'duplicates collapsed: 1' in report
    assert 'entries  : 1 (after de-duplication)' in report
    assert 'usable   : 1' in report


def test_recursive_entries_are_collapsed(tmp_path):
    parent = tmp_path / 'parent'
    child = parent / 'child'
    child.mkdir(parents=True)
    settings = Settings(
        watch={'folders': [{'path': str(parent), 'recursive': True}, {'path': str(child), 'recursive': True}]}
    )
    report = build_report(settings, str(tmp_path / 'c.toml'))
    assert 'recursive entries: 2 → collapsed to 1 watch(es)' in report


def test_estimate_uses_the_measured_coefficients(tmp_path):
    alive = tmp_path / 'alive'
    alive.mkdir()
    alive2 = tmp_path / 'alive2'
    alive2.mkdir()
    report = build_report(_settings([str(alive), str(alive2)]), str(tmp_path / 'c.toml'))
    assert f'~{2 * EST_FDS_PER_STREAM} fds' in report
    assert f'~{2 * EST_MS_PER_STREAM / 1000:.1f}s to schedule' in report


def test_empty_config_is_reported_not_crashed(tmp_path):
    report = build_report(Settings(), str(tmp_path / 'c.toml'))
    assert 'folders: none' in report
    assert 'nothing to watch' in report


def test_database_line_explains_the_env_override(tmp_path, monkeypatch):
    from config import CONFIG

    monkeypatch.setenv('SQLITE_DATABASE', str(tmp_path / 'from-env.db'))
    monkeypatch.setattr(CONFIG, 'SQLITE_DATABASE', str(tmp_path / 'from-env.db'))
    settings = Settings(database={'path': str(tmp_path / 'from-toml.db')})

    report = build_report(settings, str(tmp_path / 'c.toml'))
    assert 'env SQLITE_DATABASE wins' in report
    assert 'ignored' in report


def test_missing_config_file_is_reported(tmp_path):
    with mock.patch('src.config_check.find_config_file', return_value=None):
        report = build_report(_settings([]), None)
    assert 'none found' in report
