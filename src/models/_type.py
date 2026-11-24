from datetime import datetime
from typing import Any, NotRequired, TypedDict


class MediaParams(TypedDict):
    md5: NotRequired[str]
    title: NotRequired[str]
    # Media.ext 是 NOT NULL 列, get_or_create 的调用方 (scan 注册 / BaseMedia.__init__)
    # 都会传; 缺少它会让 Media.path 拼成 'title.ext.ext'
    ext: NotRequired[str]
    dirname: NotRequired[str]
    _created_at: NotRequired[datetime]
    updated_at: NotRequired[datetime]
    state: NotRequired[dict[str, Any]]
