from unittest import TestCase, main, mock

from config import CONFIG
from logger import logger
from media import Media, MediaTool


class TestMedia(TestCase):

    @mock.patch.object(CONFIG, 'MEDIA_FILE_PATH', '/Users/nut/Downloads/rs/202311/_/_compress/BOB-122-compress_1.mp4')
    def setUp(self) -> None:
        self.media = Media(path=CONFIG.MEDIA_FILE_PATH)
        return super().setUp()

    def test_class_methods(self):
        result = Media.get_file_info(CONFIG.MEDIA_FILE_PATH)
        result = MediaTool.read_meta_json(CONFIG.MEDIA_FILE_FOLDER)
        self.assertIsInstance(result, dict)

    def test_methods(self):
        result = self.media.metadata
        logger.info(result)
        self.assertIsInstance(result, dict)
        result = self.media.metadata.get('format').get('width')
        logger.info(result)
        self.assertIsInstance(result, (int, float))
        result = self.media.save_metadata()
        result = self.media.order_metadata
        logger.info(result)
        self.assertIsInstance(result, dict)
        result = self.media.set_metadata()
        result = self.media.decode()
        self.assertIsInstance(result, Media)

    def test_frames_count(self):
        # command = filter(lambda x: x != '', f'ffprobe -v error -select_streams v -show_streams \
        #                  {CONFIG.MEDIA_FILE_PATH} | grep nb_frames | sed -e s/nb_frames=//'.split(' '))
        # logger.info(command)
        # logger.info(list(command))
        result = self.media.frames_count
        logger.info(result)
        self.assertIsInstance(result, int)

    def test_metadata(self):
        result = self.media.metadata
        logger.info(result)
        self.assertIsInstance(result, dict)

    def test_reverse(self):
        result = self.media.reverse()
        self.assertIsInstance(result, dict)

    def test_combine(self):
        media = Media(
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
        result = self.media.trim(time=("00:00:00", "00:30:03"))
        self.assertIsInstance(result, Media)

    def test_compress(self):
        result = self.media.compress()
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    main(verbosity=2)
