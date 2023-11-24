import unittest

from config import config
from media import Media, MediaTool
from tmp.files import files


class TestMedia(unittest.TestCase):

    def test_class_methods(self):
        result = Media.get_file_info(config.MEDIA_FILE_PATH)
        result = MediaTool.read_meta_json(config.MEDIA_FILE_DIRECTORY)
        self.assertIsInstance(result, dict)

    def test_methods(self):
        media = Media(path=config.MEDIA_FILE_PATH)
        result = media.metadata
        result = media.metadata.get('format').get('width')
        result = media.save_metadata()
        result = media.order_metadata
        result = media.set_metadata()
        result = media.decode()
        self.assertIsInstance(result, dict)

    def test_reverse(self):
        media = Media(path=config.MEDIA_FILE_PATH)
        result = media.reverse()
        self.assertIsInstance(result, dict)

    def test_combine(self):
        media = Media(
            # path=config.MEDIA_FILE_PATH,
            path='/Volumes/ssd2t/lrt/_20231029_北京市华丰胡同_H265-444_Rec.2020F_4K_25_UHQ_mb05_reverse_20231029235455.mov',
            # **MediaTool.read_meta_json(config.MEDIA_FILE_DIRECTORY),
        )

        result = media.combine(
            # watermark_path='/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum.png',
            # watermark_transparent=0.3,
            audio_path='/Users/nut/Music/Music/Media.localized/Music/杨钰莹/Unknown\ Album/你看蓝蓝的天.m4a',
            audio_defer=0,
            fade_duration=1,
            # crop='4k',
            # crop_y=200,
            # reverse=True,
        )
        self.assertIsInstance(result, dict)

    def test_trim(self):
        media = Media(path=config.MEDIA_FILE_PATH)
        result = media.trim(time=("00:00:00", "00:00:03"))
        self.assertIsInstance(result, dict)

    def test_compress(self):
        media = Media(path=config.MEDIA_FILE_PATH)
        result = media.compress()
        self.assertIsInstance(result, dict)

    def test_multi_trim(self):
        result = Media.multi_trim(
            files=files,
            callback_list=[
                'compress',
            ]
        )
        self.assertIsInstance(result, list)

    def test_multi_compress(self):
        result = Media.multi_compress(
            directory=config.MEDIA_FILE_DIRECTORY,
        )
        self.assertEqual(result, None)
        # self.assertEqual(len(result), len(text))


if __name__ == '__main__':
    testcase = TestMedia()
    testcase.test_multi_compress()
    # testcase.test_multi_trim()
    # testcase.test_combine()
    # testcase.test_reverse()
    # unittest.main(verbosity=2)
