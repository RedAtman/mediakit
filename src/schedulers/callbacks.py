"""What a finished compress task means for the media row.

Both the folder scheduler (one-shot batch) and the watcher (per-file) run
compress through the same middleware, then each had its own copy of "result == 0
-> finished + soft_remove, otherwise failed". Two copies of a state machine drift;
the DB row is the thing that cannot be allowed to disagree with itself, so the
decision lives here.
"""

import logging

from src.schemas import StateChoices
from utils import file

logger = logging.getLogger()

__all__ = ['mark_compress_outcome']


def mark_compress_outcome(result) -> bool:
    """Apply one compress task's result to its media row.

    Returns True when the result carried a media row, False when there was nothing
    to settle (the caller usually does its own bookkeeping either way).
    """
    media = result.data.get('media') if getattr(result, 'data', None) else None
    if media is None:
        return False

    if result == 0:
        try:
            media.model.update_state('compress', StateChoices.finished)
        except Exception as exc:
            logger.error('update_state(finished) raised %s: %s', type(exc).__name__, exc)
        try:
            # 压缩产物已重命名, 原始文件移到 .removed/ 以便回滚
            file.soft_remove(media.path)
        except Exception as exc:
            logger.error('soft_remove(%s) raised %s: %s', media.path, type(exc).__name__, exc)
    else:
        try:
            media.model.update_state('compress', StateChoices.failed)
        except Exception as exc:
            logger.error('update_state(failed) raised %s: %s', type(exc).__name__, exc)
    return True
