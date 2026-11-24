"""探测不到元信息的文件 = 不该被当成媒体: 忽略, 不失败, 不重试.

判据是文件内容 (ffprobe 打不开), 不是扩展名 —— AppleDouble 的 `._foo.mp4` 就借了
`.mp4` 的扩展名, 扩展名只能在入口做粗筛.
"""

import subprocess
from unittest import mock

import pytest

from base.media import BaseMedia
from src.schedulers.callbacks import mark_compress_outcome
from src.schemas import StateChoices
from utils import decorator, exceptions
from utils.response import Result, ResultStatus


class _FakeMedia:
    def __init__(self):
        self.model = mock.Mock()


def test_get_metadata_raises_not_media_when_ffprobe_cannot_open():
    failure = subprocess.CalledProcessError(1, ['ffprobe'], output='Invalid data')
    with mock.patch('base.media.CommandExecutor.run', side_effect=failure):
        with pytest.raises(exceptions.NotMediaException):
            BaseMedia.get_metadata('/tmp/._clip.mp4')


def test_exception_decorator_maps_not_media_to_its_own_status():
    # 与 src/schedulers/media.py:_compress 同一种用法: 包住一个绑定方法,
    # 这样 media 能从 __self__ 拿到, 回调才有落状态的对象
    class Video:
        def compress(self):
            raise exceptions.NotMediaException(101, 'Not processable media: /tmp/._clip.mp4')

    video = Video()
    result = decorator.exception(video.compress)()

    assert isinstance(result, Result)
    assert result == ResultStatus.NOT_MEDIA
    assert result.code == 602
    assert result.data['media'] is video


def test_mark_compress_outcome_records_ignored_and_leaves_the_file_alone():
    media = _FakeMedia()
    result = Result(ResultStatus.NOT_MEDIA, data={'media': media}, msg='Not processable media')

    with mock.patch('src.schedulers.callbacks.file.soft_remove') as soft_remove:
        assert mark_compress_outcome(result) is True

    media.model.update_state.assert_called_once_with('compress', StateChoices.ignored)
    # 不是我们的文件, 不该被移进 .removed/
    soft_remove.assert_not_called()


def test_mark_compress_outcome_still_marks_failed_for_real_failures():
    media = _FakeMedia()
    result = Result(1, data={'media': media}, msg='boom')

    mark_compress_outcome(result)

    media.model.update_state.assert_called_once_with('compress', StateChoices.failed)
