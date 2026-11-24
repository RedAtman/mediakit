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


def test_get_metadata_raises_not_media_when_ffprobe_cannot_open(tmp_path):
    broken = tmp_path / '._clip.mp4'
    broken.write_bytes(b'\x00\x05\x16\x07' + b'x' * 200)
    failure = subprocess.CalledProcessError(1, ['ffprobe'], output='moov atom not found\nInvalid data found')

    with mock.patch('base.media.CommandExecutor.run', side_effect=failure):
        with pytest.raises(exceptions.NotMediaException) as caught:
            BaseMedia.get_metadata(str(broken))

    # 带上 ffprobe 的原话, 否则日志里只剩一个路径, 没法定位为什么打不开
    assert 'moov atom not found' in caught.value.msg
    assert str(broken) in caught.value.msg


def test_get_metadata_keeps_vanished_file_retryable(tmp_path):
    """文件不在 ≠ 不是媒体: 下载改名 / 卷未挂载都走这条, 必须留给 failed 重试."""
    missing = str(tmp_path / 'gone.mp4')
    failure = subprocess.CalledProcessError(1, ['ffprobe'], output='No such file or directory')

    with mock.patch('base.media.CommandExecutor.run', side_effect=failure):
        with pytest.raises(subprocess.CalledProcessError):
            BaseMedia.get_metadata(missing)


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
