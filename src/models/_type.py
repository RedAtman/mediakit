from datetime import datetime
from typing import Any, NotRequired, TypedDict


class MediaParams(TypedDict):
    md5: NotRequired[str]
    title: NotRequired[str]
    dirname: NotRequired[str]
    _created_at: NotRequired[datetime]
    updated_at: NotRequired[datetime]
    state: NotRequired[dict[str, Any]]
