"""dedupe 的目录来源必须与 watch 同源.

回归: dedupe 曾只认清单文件, 于是"把目录配进 config.toml 的 [[watch.folders]]"
之后它一个都看不见, 还会提示用户去创建那个已经存在的配置文件.
"""

from unittest import mock

import pytest

from src.config_file import Settings
from src.schedulers.dedupe import _resolve_folders


def test_config_folders_win_over_the_list_file(tmp_path):
    listing = tmp_path / 'folders.txt'
    listing.write_text('/from-list\n', encoding='utf-8')
    settings = Settings(watch={'folders': [{'path': '/from-config/a'}, {'path': '/from-config/b'}]})

    with mock.patch('src.schedulers.dedupe.load_settings', return_value=settings):
        assert _resolve_folders(str(listing), None) == ['/from-config/a', '/from-config/b']


def test_falls_back_to_the_plain_list(tmp_path):
    listing = tmp_path / 'folders.txt'
    listing.write_text('# comment\n/one\n/two\n', encoding='utf-8')

    with mock.patch('src.schedulers.dedupe.load_settings', return_value=Settings()):
        assert _resolve_folders(str(listing), None) == ['/one', '/two']


def test_missing_everything_is_a_readable_exit(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg'))
    with mock.patch('src.schedulers.dedupe.load_settings', return_value=Settings()):
        with mock.patch('src.schedulers.dedupe.find_folder_file', return_value=None):
            with pytest.raises(SystemExit) as caught:
                _resolve_folders(None, None)
    assert 'no folders to scan' in str(caught.value)


def test_warns_when_both_config_and_folder_file_are_given(tmp_path):
    listing = tmp_path / 'folders.txt'
    listing.write_text('/x\n', encoding='utf-8')
    settings = Settings(watch={'folders': [{'path': '/from-config'}]})

    with mock.patch('src.schedulers.dedupe.load_settings', return_value=settings):
        with mock.patch('src.schedulers.dedupe.logger') as logger:
            assert _resolve_folders(str(listing), None) == ['/from-config']
    logger.warning.assert_called_once()
