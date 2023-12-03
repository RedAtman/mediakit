from unittest import TestCase, main, mock

from _pytest.monkeypatch import V

from config import CONFIG
from logger import logger
from base.media import BaseMedia
from base.video import Video


class TestVideo(TestCase):

    @mock.patch.object(CONFIG, 'MEDIA_FILE_PATH', 'samples/zh.mp4')
    def setUp(self) -> None:
        self.video = Video(path=CONFIG.MEDIA_FILE_PATH)
        return super().setUp()

    def test_class_methods(self):
        result = Video.get_file_info(CONFIG.MEDIA_FILE_PATH)
        self.assertIsInstance(result, dict)

    def test_methods(self):
        result = self.video.metadata
        logger.info(result)
        self.assertIsInstance(result, dict)
        result = self.video.metadata.get('format').get('width')
        logger.info(result)
        self.assertIsInstance(result, (int, float))
        result = self.video.save_metadata()
        result = self.video.order_metadata
        logger.info(result)
        self.assertIsInstance(result, dict)
        result = self.video.set_metadata()
        result = self.video.decode()
        self.assertIsInstance(result, Video)

    def test_frames_count(self):
        result = self.video.frames_count
        logger.info(result)
        self.assertIsInstance(result, int)

    def test_metadata(self):
        result = self.video.metadata
        logger.info(result)
        self.assertIsInstance(result, dict)

    def test_reverse(self):
        result = self.video.reverse()
        self.assertIsInstance(result, dict)

    def test_combine(self):
        media = Video(
            # path=CONFIG.MEDIA_FILE_PATH,
            path='/Volumes/ssd2t/lrt/_20231029_北京市华丰胡同_H265-444_Rec.2020F_4K_25_UHQ_mb05_reverse_20231029235455.mov',
            # **MediaTool.read_meta_json(CONFIG.MEDIA_FILE_FOLDER),
        )

        result = media.combine(
            # watermark_path='/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum.png',
            # watermark_transparent=0.3,
            audio_path='/Users/nut/Music/Music/Media.localized/Music/杨钰莹/Unknown Album/你看蓝蓝的天.m4a',
            audio_defer=0,
            fade_duration=1,
            # crop='4k',
            # crop_y=200,
            # reverse=True,
        )
        self.assertIsInstance(result, dict)

    def test_trim(self):
        result = self.video.trim(trim_time=("00:00:00", "00:00:03"))
        self.assertIsInstance(result, BaseMedia)

    def test_compress(self):
        result = self.video.compress()
        self.assertIsInstance(result, dict)

    def test_save_text(self):
        result = self.video.save_text()
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    main(verbosity=2)
