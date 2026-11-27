"""~/.config/mediakit/config.toml: 加载/校验/按路径解析.

配置非法必须当场报错 (daemon 静默忽略一个写错的 key 比拒绝启动更糟).
"""

from pathlib import Path
from unittest import mock

import pytest

from src.config_file import (
    EXAMPLE_CONFIG_TEXT,
    ConfigError,
    FolderEntry,
    Resolver,
    Settings,
    apply_database_path,
    config_dir,
    default_config_path,
    find_config_file,
    load_settings,
    write_starter_config,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_config_dir_honours_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg'))
    assert config_dir() == tmp_path / 'xdg' / 'mediakit'
    assert default_config_path() == tmp_path / 'xdg' / 'mediakit' / 'config.toml'


def test_config_dir_falls_back_to_dot_config(monkeypatch, tmp_path):
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))
    assert config_dir() == tmp_path / '.config' / 'mediakit'


def test_find_config_file_precedence(monkeypatch, tmp_path):
    explicit = tmp_path / 'explicit.toml'
    explicit.write_text('[watch]\n', encoding='utf-8')
    env_file = tmp_path / 'env.toml'
    env_file.write_text('[watch]\n', encoding='utf-8')

    assert find_config_file(explicit) == explicit
    monkeypatch.setenv('MEDIAKIT_CONFIG', str(env_file))
    assert find_config_file(None) == env_file
    # 显式参数仍然压过环境变量
    assert find_config_file(explicit) == explicit

    monkeypatch.delenv('MEDIAKIT_CONFIG')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'empty'))
    assert find_config_file(None) is None


def test_missing_explicit_config_is_an_error(tmp_path):
    # 配置缺失是 ConfigError 而不是 FileNotFoundError: cli 只把这一类翻译成人读的退出信息
    with pytest.raises(ConfigError):
        find_config_file(tmp_path / 'nope.toml')


def test_absent_config_yields_empty_settings(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    settings = load_settings()
    assert settings.watch.folders == []
    assert settings.watch.cpu_limit is None


def test_load_settings_parses_folders_and_defaults(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text(
        """
[compress]
fps = 24

[watch]
cpu_limit = 150

[[watch.folders]]
path = "~/Downloads/rs/jp.gv"
media_type = "video"
recursive = true
compress = { resolution = "HD", fps = 30 }

[[watch.folders]]
path = "~/Downloads/rs/one"
compress = { resolution = "FHD" }
""",
        encoding='utf-8',
    )
    settings = load_settings(path)

    assert settings.watch.cpu_limit == 150
    jp, one = settings.watch.folders
    assert jp.path.endswith('Downloads/rs/jp.gv') and jp.recursive is True
    assert jp.compress.resolution == 'HD' and jp.compress.fps == 30
    assert one.media_type is None and one.recursive is None


@pytest.mark.parametrize(
    'body, fragment',
    [
        ('[watch]\nnope = 1\n', 'nope'),
        ('[[watch.folders]]\npath = "relative/dir"\n', 'absolute'),
        ('[[watch.folders]]\npath = "~/x"\nmedia_type = "nope"\n', 'media_type'),
        ('[compress]\nresolution = "1080p"\n', 'resolution'),
        ('[compress]\nfps = 0\n', 'fps'),
        ('this is not = toml [[[\n', 'TOML'),
    ],
)
def test_invalid_config_is_rejected_at_load(tmp_path, body, fragment):
    path = tmp_path / 'config.toml'
    path.write_text(body, encoding='utf-8')
    with pytest.raises(ValueError) as caught:
        load_settings(path)
    assert fragment in str(caught.value)


def test_resolver_uses_longest_prefix_and_layers_compress_options():
    settings = Settings(
        watch={
            'folders': [
                {'path': '/a/b', 'compress': {'resolution': 'HD'}},
                {'path': '/a/b/c', 'recursive': True, 'compress': {'resolution': 'FHD', 'fps': 60}},
            ]
        },
        compress={'fps': 24},
    )
    resolver = Resolver(settings)

    assert resolver.entry_for('/a/b/c/deep/x.mp4').path == '/a/b/c'
    assert resolver.entry_for('/a/b/x.mp4').path == '/a/b'
    assert resolver.entry_for('/other/x.mp4') is None
    # 深路径: 覆盖 resolution/fps
    assert resolver.compress_opts_for('/a/b/c/x.mp4', {}) == {'resolution': 'FHD', 'fps': 60}
    # 浅路径: 自己那条 + 全局 fps
    assert resolver.compress_opts_for('/a/b/x.mp4', {}) == {'resolution': 'HD', 'fps': 24}
    # 未配置路径: 只剩全局缺省
    assert resolver.compress_opts_for('/other/x.mp4', {}) == {'fps': 24}
    # CLI 显式给的参数最高优先: 显式 flag 永远压过配置文件
    assert resolver.compress_opts_for('/a/b/c/x.mp4', {'resolution': 'UHD'}) == {'resolution': 'UHD', 'fps': 60}
    # CLI 没给的键仍然来自配置
    assert resolver.compress_opts_for('/a/b/c/x.mp4', {'fps': 25}) == {'resolution': 'FHD', 'fps': 25}
    assert resolver.recursive_for('/a/b/c/deep', False) is True
    assert resolver.recursive_for('/a/b', True) is True


def test_folder_entry_normalises_path():
    entry = FolderEntry(path='~/Downloads//rs/../rs/x/')
    assert entry.path.endswith('/Downloads/rs/x')


def test_load_settings_reads_the_default_location(monkeypatch, tmp_path):
    cfg_dir = tmp_path / 'mediakit'
    cfg_dir.mkdir()
    (cfg_dir / 'config.toml').write_text('[[watch.folders]]\npath = "~/x"\n', encoding='utf-8')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    monkeypatch.delenv('MEDIAKIT_CONFIG', raising=False)
    assert len(load_settings().watch.folders) == 1


def test_load_settings_does_not_swallow_toml_errors(monkeypatch, tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text('[watch\n', encoding='utf-8')
    with mock.patch('src.config_file.tomllib.loads', side_effect=ValueError('boom')):
        with pytest.raises(ValueError):
            load_settings(path)


def test_folders_file_expands_into_entries_and_explicit_wins(tmp_path):
    listing = tmp_path / 'folders.txt'
    listing.write_text('# 旧清单\n/tmp/a\n/tmp/b\n/tmp/a\n', encoding='utf-8')

    settings = Settings(watch={'folders_file': str(listing), 'folders': [{'path': '/tmp/b', 'recursive': True}]})
    paths = [entry.path for entry in settings.watch.folders]
    # 显式条目在前且不被清单覆盖; 清单里的重复路径被去掉
    assert paths == ['/tmp/b', '/tmp/a']
    resolver = settings.resolver()
    assert resolver.recursive_for('/tmp/b/x.mp4', False) is True


def test_folders_file_must_be_absolute():
    with pytest.raises(ValueError):
        Settings(watch={'folders_file': 'relative/list.txt'})


def test_repo_examples_cannot_drift_from_the_code():
    """仓库里的示例必须与代码里的常量/解析器一致, 否则文档会悄悄腐烂."""
    assert (REPO_ROOT / 'config.toml.example').read_text(encoding='utf-8') == EXAMPLE_CONFIG_TEXT
    # 示例本身要能通过同一套校验 (它故意不含生效目录, 所以只验参数)
    settings = load_settings(REPO_ROOT / 'config.toml.example')
    assert settings.watch.folders == []
    assert settings.watch.cpu_limit == 200
    assert settings.compress.fps == 24

    from src.file.paths import parse_folder_file

    listed = parse_folder_file(str(REPO_ROOT / 'folders.txt.example'))
    assert listed == [str(Path(p).expanduser()) for p in listed]
    assert len(listed) == 2


def test_write_starter_config_writes_and_refuses_overwrite(tmp_path):
    target = tmp_path / 'nested' / 'config.toml'
    written = write_starter_config(target)
    assert written == target
    assert written.read_text(encoding='utf-8') == EXAMPLE_CONFIG_TEXT
    # 生成的文件同样要是合法配置
    assert load_settings(written).watch.cpu_limit == 200

    with pytest.raises(FileExistsError):
        write_starter_config(target)


def test_database_path_is_expanded_and_must_be_absolute():
    settings = Settings(database={'path': '~/state/db.db'})
    assert settings.database.path == str(Path('~/state/db.db').expanduser())
    with pytest.raises(ValueError):
        Settings(database={'path': 'relative/db.db'})


def test_apply_database_path_sets_config_and_creates_parent(tmp_path, monkeypatch):
    from config import CONFIG
    from src.db import DatabaseEngine

    monkeypatch.delenv('SQLITE_DATABASE', raising=False)
    target = tmp_path / 'state' / 'custom.db'
    monkeypatch.setattr(CONFIG, 'SQLITE_DATABASE', str(tmp_path / 'old.db'))
    DatabaseEngine.reset()

    applied = apply_database_path(Settings(database={'path': str(target)}))

    assert applied == str(target)
    assert CONFIG.SQLITE_DATABASE == str(target)
    assert target.parent.is_dir()  # engine 建库时不会替你建目录
    DatabaseEngine.reset()


def test_env_database_wins_over_the_config_file(tmp_path, monkeypatch):
    from config import CONFIG

    monkeypatch.setenv('SQLITE_DATABASE', str(tmp_path / 'from-env.db'))
    monkeypatch.setattr(CONFIG, 'SQLITE_DATABASE', str(tmp_path / 'from-env.db'))

    with mock.patch('src.config_file.logger') as logger:
        assert apply_database_path(Settings(database={'path': str(tmp_path / 'from-toml.db')})) is None

    assert CONFIG.SQLITE_DATABASE == str(tmp_path / 'from-env.db')
    logger.warning.assert_called_once()
    message = logger.warning.call_args[0][0]
    # 必须告诉用户"怎么让配置文件生效", 不只说谁赢
    assert 'wins over' in message
    assert '.env' in message


def test_no_database_section_is_a_noop(tmp_path, monkeypatch):
    from config import CONFIG

    monkeypatch.delenv('SQLITE_DATABASE', raising=False)
    before = CONFIG.SQLITE_DATABASE
    assert apply_database_path(Settings()) is None
    assert CONFIG.SQLITE_DATABASE == before


def test_resolver_caches_the_canonical_path(tmp_path):
    """一次 flush 里同一路径会被查 2-3 次, realpath 只该算一次."""
    import src.config_file as config_file
    from src.config_file import Resolver, Settings

    config_file._canonical.cache_clear()
    resolver = Resolver(Settings(watch={'folders': [{'path': '/a/b'}, {'path': '/a/b/c'}]}))
    after_construction = config_file._canonical.cache_info()

    for _ in range(3):
        resolver.media_type_for('/a/b/c/x.mp4', 'video')
        resolver.recursive_for('/a/b/c/x.mp4', False)
        resolver.compress_opts_for('/a/b/c/x.mp4', {})

    info = config_file._canonical.cache_info()
    # 构造时每条 entry 各 miss 一次, 之后同一路径只 miss 一次, 其余全部命中
    assert after_construction.misses == 2
    assert info.misses == after_construction.misses + 1
    assert info.hits >= 8
    config_file._canonical.cache_clear()


def test_resolver_still_matches_through_symlinks(tmp_path):
    """/tmp 与 /private/tmp 是同一处: 缓存不能破坏这条."""
    import src.config_file as config_file

    config_file._canonical.cache_clear()
    real = tmp_path / 'media'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    settings = Settings(watch={'folders': [{'path': str(real)}]})
    resolver = settings.resolver()
    assert resolver.entry_for(str(link / 'x.mp4')) is not None
    config_file._canonical.cache_clear()
