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

    def _command(self, source_wh, audio_streams=None, **kwargs):
        """audio_streams: 音轨列表, codec_name 缺失即视为解不了; None = 一条可解码的 AAC 音轨."""
        if audio_streams is None:
            audio_streams = [{'index': 1, 'codec_type': 'audio', 'codec_name': 'aac'}]
        video = object.__new__(Video)
        video.path = '/tmp/src.mp4'
        with (
            mock.patch.object(Video, 'resolution', new_callable=mock.PropertyMock, return_value=source_wh),
            mock.patch.object(Video, 'audio_streams', new_callable=mock.PropertyMock, return_value=audio_streams),
            mock.patch.object(
                Video,
                'decodable_audio_indexes',
                new_callable=mock.PropertyMock,
                return_value=[i for i, s in enumerate(audio_streams) if s.get('codec_name')],
            ),
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

    def test_no_decodable_audio_falls_back_to_video_only(self):
        # AVI 音轨 codec_tag 'qg[0][0]' 认不出 -> ffmpeg 建流即 EINVAL, 连视频都不编
        command = self._command((640, 480), audio_streams=[{'codec_type': 'audio', 'codec_tag_string': 'qg[0][0]'}])
        assert '-an' in command
        assert '-c:a' not in command

    def test_decodable_audio_keeps_aac(self):
        command = self._command((640, 480))
        assert command[command.index('-c:a') + 1] == 'aac'
        assert '-an' not in command
        # 全部音轨都好时维持自动映射, 不要凭空多出 -map 改变选流
        assert '-map' not in command

    def test_partially_decodable_audio_keeps_the_good_streams(self):
        # 第二条音轨 codec 认不出: 只有第一条留下, 且必须显式 map (给了 -map 就不再自动选流)
        command = self._command(
            (640, 480),
            audio_streams=[
                {'codec_type': 'audio', 'codec_name': 'aac'},
                {'codec_type': 'audio', 'codec_tag_string': 'qg[0][0]'},
            ],
        )
        maps = [command[i + 1] for i, part in enumerate(command) if part == '-map']
        assert maps == ['0:v:0', '0:a:0']
        assert command[command.index('-c:a') + 1] == 'aac'
        assert '-an' not in command

    def test_mapping_uses_audio_relative_index(self):
        # 坏的是第一条, 好的那条是 -map 0:a:1 而不是按流 index 算
        command = self._command(
            (640, 480),
            audio_streams=[
                {'codec_type': 'audio', 'codec_tag_string': 'qg[0][0]'},
                {'codec_type': 'audio', 'codec_name': 'aac'},
            ],
        )
        maps = [command[i + 1] for i, part in enumerate(command) if part == '-map']
        assert maps == ['0:v:0', '0:a:1']

    def test_explicit_resolution_and_fps(self):
        command = self._command((3840, 2160), resolution='FHD', fps=30)
        assert 'scale=1920:1080:' in command[command.index('-vf') + 1]
        assert command[command.index('-r') + 1] == '30'

    def test_config_fallback_overridable(self):
        with mock.patch.object(CONFIG, 'COMPRESS_RESOLUTION', 'UHD'), mock.patch.object(CONFIG, 'COMPRESS_FPS', 60):
            command = self._command((7680, 4320))
        assert 'scale=3840:2160:' in command[command.index('-vf') + 1]
        assert command[command.index('-r') + 1] == '60'
