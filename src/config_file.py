"""TOML config for the watch daemon (`~/.config/mediakit/config.toml`).

Why a file instead of flags: the daemon has a per-directory axis (325 entries in
the current list) plus per-directory overrides, and a plain text list cannot
express "this subtree is 720p, that one is recursive". TOML is stdlib-parsable
(`tomllib`), comment-friendly and validates with pydantic.

Location follows XDG on purpose: config belongs in `~/.config`, while state
(`logs/`, `db.db`) stays in the platform state dir that `config.py` already
computes. macOS is not special-cased here because this machine's tooling already
lives in `~/.config`.
"""

import logging
import os
from pathlib import Path
import sys
import tomllib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.file.paths import parse_folder_file
from utils.media import MEDIA_CATEGORIES
from utils.video import VideoResolution

logger = logging.getLogger()

__all__ = [
    'CONFIG_ENV_VAR',
    'ConfigError',
    'CompressOptions',
    'FolderEntry',
    'Resolver',
    'Settings',
    'config_dir',
    'default_config_path',
    'find_config_file',
    'load_settings',
]

CONFIG_ENV_VAR = 'MEDIAKIT_CONFIG'
CONFIG_FILENAME = 'config.toml'


class ConfigError(ValueError):
    """配置不可用: 让调用方可以只捕获这一类, 而不是所有 ValueError."""


class CompressOptions(BaseModel):
    """Values handed to `Video.compress`; None means "not specified here"."""

    model_config = ConfigDict(extra='forbid')

    resolution: str | None = None
    fps: int | None = Field(default=None, ge=1)

    @field_validator('resolution')
    @classmethod
    def _known_resolution(cls, value: str | None) -> str | None:
        # 提前到加载期报错: 否则要到第一个文件压缩时才发现 "1080p" 不认识
        if value is not None:
            VideoResolution.parse(value)
        return value


class FolderEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    path: str
    # 'image' 合法但 MEDIA_CLASSES 里还没有实现, 与 CLI 的 -t 保持同一套词表
    media_type: str | None = None
    recursive: bool | None = None
    compress: CompressOptions | None = None

    @field_validator('path')
    @classmethod
    def _absolute(cls, value: str) -> str:
        expanded = os.path.normpath(os.path.expanduser(value))
        if not os.path.isabs(expanded):
            raise ValueError(f'folder path must be absolute or start with ~, got {value!r}')
        return expanded

    @field_validator('media_type')
    @classmethod
    def _known_media_type(cls, value: str | None) -> str | None:
        if value is not None and value not in MEDIA_CATEGORIES:
            raise ValueError(f'media_type must be one of {MEDIA_CATEGORIES}, got {value!r}')
        return value


class WatchSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')

    cpu_limit: int | None = Field(default=None, ge=1)
    # 旧的纯文本清单可以直接在这里引用, 不必把 300+ 行改写成 [[watch.folders]]
    folders_file: str | None = None
    folders: list[FolderEntry] = Field(default_factory=list)

    @model_validator(mode='after')
    def _expand_folders_file(self):
        """把 folders_file 里的路径展开成普通条目, 让 Resolver 只有一种输入形式."""
        if not self.folders_file:
            return self
        listed = os.path.normpath(os.path.expanduser(self.folders_file))
        if not os.path.isabs(listed):
            raise ValueError(f'watch.folders_file must be absolute or start with ~, got {self.folders_file!r}')
        known = {os.path.realpath(entry.path) for entry in self.folders}
        for path in parse_folder_file(listed):
            if os.path.realpath(path) not in known:
                self.folders.append(FolderEntry(path=path))
                known.add(os.path.realpath(path))
        return self


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')

    watch: WatchSettings = Field(default_factory=WatchSettings)
    compress: CompressOptions = Field(default_factory=CompressOptions)

    def resolver(self) -> 'Resolver':
        return Resolver(self)


class Resolver:
    """Longest-prefix lookup from an event path to the entry that governs it.

    watch 侧只有一个去抖缓冲/一个 handler, 所以"每路径不同参数"只能靠查表:
    `/a/b/c/x.mp4` 命中 `/a/b/c` 而不是 `/a/b`.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        # 两边都取 realpath 再比: 事件路径来自 watchdog (未被 _normalize_path 处理),
        # 而 flush 里用的是 realpath, 且 macOS 上 /tmp 与 /private/tmp 是同一处.
        self._entries = sorted(
            ((os.path.realpath(entry.path), entry) for entry in self.settings.watch.folders),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )

    def entry_for(self, path: str):
        canonical = os.path.realpath(path)
        for prefix, entry in self._entries:
            if canonical == prefix or canonical.startswith(prefix + os.sep):
                return entry
        return None

    def paths(self) -> list[str]:
        return [prefix for prefix, _entry in self._entries]

    def media_type_for(self, path: str, default: str) -> str:
        entry = self.entry_for(path)
        return (entry.media_type if entry else None) or default

    def recursive_for(self, path: str, default: bool) -> bool:
        entry = self.entry_for(path)
        return default if entry is None or entry.recursive is None else entry.recursive

    def compress_opts_for(self, path: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """[compress] 是全局缺省, 逐目录的 compress 覆盖它, 未指定的键保留上一层."""
        opts: dict[str, Any] = dict(default or {})
        entry = self.entry_for(path)
        for layer in (self.settings.compress, entry.compress if entry else None):
            if layer is None:
                continue
            if layer.resolution is not None:
                opts['resolution'] = layer.resolution
            if layer.fps is not None:
                opts['fps'] = layer.fps
        return opts


def config_dir() -> Path:
    if sys.platform == 'win32':
        base = os.getenv('APPDATA') or os.path.expanduser('~/AppData/Roaming')
    else:
        base = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return Path(base) / 'mediakit'


def default_config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def find_config_file(explicit: str | Path | None = None) -> Path | None:
    """--config > MEDIAKIT_CONFIG > ~/.config/mediakit/config.toml > None."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ConfigError(f'config file not found: {path}')
        return path
    env = os.getenv(CONFIG_ENV_VAR)
    if env:
        path = Path(env).expanduser()
        if not path.is_file():
            raise ConfigError(f'{CONFIG_ENV_VAR} points at a missing file: {path}')
        return path
    path = default_config_path()
    return path if path.is_file() else None


def load_settings(explicit: str | Path | None = None) -> Settings:
    """Load and validate the config file; an absent file is an empty Settings.

    Parse/validation errors propagate: a daemon that silently ignores a typo in
    its config is worse than one that refuses to start.
    """
    path = find_config_file(explicit)
    if path is None:
        return Settings()
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as err:
        raise ConfigError(f'invalid TOML in {path}: {err}') from err
    try:
        return Settings(**data)
    except Exception as err:
        detail = ' '.join(str(err).split())
        raise ConfigError(f'invalid config {path}: {detail[:400]}') from err
