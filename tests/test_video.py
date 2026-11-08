import logging
import os
import shutil
import tempfile
from unittest import TestCase, mock

from base.video import Video

logger = logging.getLogger()


class TestVideo(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.temp_video = os.path.join(self.temp_dir, 'test_video.mp4')
        with open(self.temp_video, 'w') as f:
            f.write('dummy video content')

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_video(self) -> Video:
        """构造 Video 实例且不触碰真实 DB (get_or_create 走 mock)"""
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_model.get_or_create.return_value = mock.MagicMock()
            return Video(path=self.temp_video)

    def _run(self, video_method, *args, **kwargs):
        """执行 ffmpeg 封装方法并返回它拼出的 command 列表 (不真正调用 ffmpeg)"""
        with (
            mock.patch.object(Video, 'create_file_path', return_value='/tmp/out.mp4'),
            mock.patch('utils.decorator.CommandExecutor.run', return_value='ok') as run,
        ):
            result = video_method(*args, **kwargs)
        return run.call_args[0][0], result

    def test_construct_sets_file_info(self):
        video = self._make_video()
        assert video.path == self.temp_video
        assert video.title == 'test_video'
        assert video.ext == 'mp4'

    @mock.patch('base.media.calculate_md5', return_value='test_md5_hash')
    def test_md5_comes_from_calculate_md5(self, mock_md5):
        video = self._make_video()
        assert video.md5 == 'test_md5_hash'
        mock_md5.assert_called_once_with(self.temp_video)

    def test_width_height_reads_video_stream(self):
        video = self._make_video()
        probe = {'format': {}, 'streams': [{'codec_type': 'audio'}, {'width': 3840, 'height': 2160}]}
        # 只 mock ffprobe 的 I/O, width_height 的选取逻辑还是真的
        with mock.patch.object(Video, 'get_metadata', return_value=probe):
            assert video.width_height == (3840, 2160)

    def test_convert_format_re_encodes_video_and_copies_audio(self):
        video = self._make_video()
        command, result = self._run(video.convert_format, ext='mov')

        assert command[command.index('-i') + 1] == self.temp_video
        assert command[command.index('-c:v') + 1] == 'libx265'
        assert command[command.index('-c:a') + 1] == 'copy'
        assert command[-1] == '/tmp/out.mp4'
        assert result['new_file_path'] == '/tmp/out.mp4'

    def test_trim_passes_seek_window(self):
        video = self._make_video()
        command, _ = self._run(video.trim, trim_time=('00:00:01', '00:00:03'))

        # trim 拼的是 f-string 命令而不是 list, 所以按子串断言
        assert '-ss 00:00:01' in command
        assert '-to 00:00:03' in command
        assert '-accurate_seek' in command

    def test_trim_rejects_bad_trim_time(self):
        video = self._make_video()
        # 非序列 / 长度不为2 都必须报 ValueError, 而不是等到解包时才炸或爆 TypeError
        for bad in ('00:00:01', None, ('00:00:01',), ('a', 'b', 'c')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                video.trim(trim_time=bad)
