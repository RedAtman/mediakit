from unittest import TestCase, mock

from base.video import Video
from config import CONFIG
from utils.video import VideoResolution


class TestResolutionParse(TestCase):
    def test_enum_passthrough(self):
        assert VideoResolution.parse(VideoResolution.FHD) is VideoResolution.FHD

    def test_enum_name_case_insensitive(self):
        assert VideoResolution.parse('fhd') is VideoResolution.FHD
        assert VideoResolution.parse(' UHD ') is VideoResolution.UHD

    def test_wxh(self):
        assert VideoResolution.parse('1920x1080') is VideoResolution.FHD
        assert VideoResolution.parse('1280*720') is VideoResolution.HD

    def test_unknown_raises(self):
        # '1080p'/'4k' 这类缩写不在枚举命名体系内, 必须报错而不是静默回退兜底值
        for bad in ('1080p', '4k', '999x999', '', None):
            with self.assertRaises(ValueError):
                VideoResolution.parse(bad)


class TestCompressCommand(TestCase):
    """只验证 command 拼装, 不真跑 ffmpeg。"""

    def _command(self, source_wh, **kwargs):
        video = object.__new__(Video)
        video.path = '/tmp/src.mp4'
        with (
            mock.patch.object(Video, 'resolution', new_callable=mock.PropertyMock, return_value=source_wh),
            mock.patch.object(Video, 'create_file_path', return_value='/tmp/out.mp4'),
            mock.patch('utils.decorator.CommandExecutor.run', return_value='done') as run,
        ):
            video.compress(**kwargs)
        return run.call_args[0][0]

    def test_default_fallback_from_config(self):
        command = self._command((3840, 2160))
        assert '-vf' in command
        assert 'scale=1280:720:' in command[command.index('-vf') + 1]
        assert command[command.index('-r') + 1] == str(CONFIG.COMPRESS_FPS)

    def test_no_upscale(self):
        command = self._command((640, 480))
        assert '-vf' not in command

    def test_explicit_resolution_and_fps(self):
        command = self._command((3840, 2160), resolution='FHD', fps=30)
        assert 'scale=1920:1080:' in command[command.index('-vf') + 1]
        assert command[command.index('-r') + 1] == '30'

    def test_config_fallback_overridable(self):
        with mock.patch.object(CONFIG, 'COMPRESS_RESOLUTION', 'UHD'), mock.patch.object(CONFIG, 'COMPRESS_FPS', 60):
            command = self._command((7680, 4320))
        assert 'scale=3840:2160:' in command[command.index('-vf') + 1]
        assert command[command.index('-r') + 1] == '60'
