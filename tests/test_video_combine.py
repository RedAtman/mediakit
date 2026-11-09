"""Video.combine 的 filter/命令组装 — 纯字符串构造, 不需要真的跑 ffmpeg.

combine 是项目里最长的函数, 拆成几个 builder 之前先把现有输出钉住, 否则
filter_complex 的片段顺序一改就没人能证明行为没变.
"""

import unittest
from unittest import mock

from base.video import Video
from utils.command import CommandExecutor

PROBE = {'streams': [{'duration': '10.0'}], 'format': {}}


def _make_video() -> Video:
    """一个不探测媒体的 Video: metadata 用 patch 提供, 免得真调 ffprobe."""
    video = Video.__new__(Video)
    video.path = '/tmp/source.mp4'
    video.dirname = '/tmp'
    video.title = 'source'
    video.ext = 'mp4'
    return video


class TestCombineCommand(unittest.TestCase):
    def _combine(self, **kwargs) -> list[str]:
        """返回 combine 交给 ffmpeg 的命令数组.

        combine 带 @decorator.timer/@decorator.execute, 本身不返回命令: 直接抓
        CommandExecutor.run 的入参, 也算顺带验证了真正被执行的就是这条命令.
        """
        video = _make_video()
        with (
            mock.patch.object(Video, 'get_output_path', return_value='/tmp/out.mp4'),
            mock.patch.object(Video, 'get_metadata', return_value=PROBE),
            # monitor 会去算 frames_count (真调 ffprobe), 这里不需要进度条
            mock.patch.object(Video, 'monitor', None),
            mock.patch.object(CommandExecutor, 'run', return_value='') as mock_run,
        ):
            result = video.combine(**kwargs)

        self.assertEqual(result['new_file_path'], '/tmp/out.mp4')
        return mock_run.call_args.args[0]

    @staticmethod
    def _filter_complex(command: list[str]) -> str:
        return command[command.index('-filter_complex') + 1]

    def test_source_video_is_the_first_input(self):
        """滤镜里 [0:v] 指源视频, 所以它必须是第一个 -i; 少了它 ffmpeg 直接报错."""
        command = self._combine(watermark_path='/tmp/logo.png', audio_path='/tmp/music.mp3', crop='1080p')

        inputs = [command[i + 1] for i, arg in enumerate(command) if arg == '-i']
        self.assertEqual(inputs, ['/tmp/source.mp4', '/tmp/logo.png', '/tmp/music.mp3'])

    def test_watermark_and_audio_and_crop(self):
        command = self._combine(watermark_path='/tmp/logo.png', audio_path='/tmp/music.mp3', crop='1080p')
        filters = self._filter_complex(command)

        # 视频先缩放裁剪, 再和 logo 做 scale2ref, 最后 overlay
        self.assertIn('[0:v]scale=4096:-1[video_step_zero];[video_step_zero]crop=1920:1080:0:0', filters)
        self.assertIn('scale2ref', filters)
        self.assertIn('colorchannelmixer=aa=0.3', filters)
        self.assertIn('overlay=(main_w-w)*0.7:(main_h-h)*0.7', filters)
        # 音轨淡入淡出, 长度取视频时长减 1 秒
        self.assertIn('afade=t=in:st=0:d=1', filters)
        self.assertIn('afade=t=out:st=9.0:d=1', filters)
        # 输入顺序: 源视频 -> logo -> 音频 (由 test_source_video_is_the_first_input 逐项校验)
        self.assertIn('/tmp/logo.png', command)
        self.assertIn('/tmp/music.mp3', command)

    def test_audio_without_watermark_keeps_the_audio_filter(self):
        """曾经 filter_complex[0] 被按索引覆盖, 无 logo 时音频滤镜会被抹掉."""
        command = self._combine(watermark_path=None, audio_path='/tmp/music.mp3', crop='1080p')
        filters = self._filter_complex(command)

        self.assertIn('[1:a]', filters, '无 logo 时音频是第 2 个输入')
        self.assertIn('afade=t=in', filters)
        self.assertNotIn('overlay', filters)

    def test_crop_only(self):
        command = self._combine(watermark_path=None, audio_path=None, crop='1080p')
        filters = self._filter_complex(command)
        expected = '[0:v]scale=4096:-1[video_step_zero];[video_step_zero]crop=1920:1080:0:0[video_step_one]'
        self.assertEqual(filters, expected)

    def test_reverse_is_appended_to_the_video_chain(self):
        command = self._combine(watermark_path=None, audio_path=None, crop='1080p', reverse=True)
        self.assertIn('crop=1920:1080:0:0,reverse', self._filter_complex(command))

    def test_unknown_crop_contributes_no_video_filter(self):
        command = self._combine(watermark_path=None, audio_path=None, crop='nope')
        self.assertNotIn('-filter_complex', command)

    def test_nothing_requested(self):
        command = self._combine(watermark_path=None, audio_path=None, crop=None)
        self.assertIn('-x265-params', command)
        self.assertIn('crf=8', command)
