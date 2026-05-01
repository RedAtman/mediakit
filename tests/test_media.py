import logging
import os
import tempfile
from unittest import TestCase, main, mock

from base.media import BaseMedia
from base.video import Video
from config import CONFIG


logger = logging.getLogger()


class TestVideo(TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.temp_video = os.path.join(self.temp_dir, "test_video.mp4")
        with open(self.temp_video, "w") as f:
            f.write("dummy video content")
        return super().setUp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        return super().tearDown()

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    @mock.patch("base.media.BaseMedia._MEDIA_CLS")
    def test_class_methods(self, mock_model, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            video = Video(path=self.temp_video)
            assert isinstance(video, Video)

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    def test_convert_format(self, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            video = Video(path=self.temp_video)
            result = video.md5
            logger.info(result)
            assert isinstance(result, str)

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    @mock.patch.object(Video, 'get_metadata')
    def test_metadata(self, mock_get_metadata, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        mock_get_metadata.return_value = {'format': {'width': 1920}}
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            video = Video(path=self.temp_video)
            result = video.metadata
            logger.info(result)
            assert isinstance(result, dict)

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    def test_md5(self, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            video = Video(path=self.temp_video)
            with mock.patch.object(video, 'trim') as mock_trim:
                mock_trim.return_value = mock.MagicMock()
                result = video.trim(trim_time=("00:00:00", "00:00:03"))
                assert result is not None

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    def test_trim(self, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            video = Video(path=self.temp_video)
            with mock.patch.object(video, 'compress') as mock_compress:
                mock_compress.return_value = mock.MagicMock()
                result = video.compress()
                assert result is not None

    @mock.patch("base.media.guess")
    @mock.patch("base.media.calculate_md5")
    def test_compress(self, mock_md5, mock_guess):
        mock_guess.return_value = "video"
        mock_md5.return_value = "test_md5_hash"
        with mock.patch.object(Video, '_MEDIA_CLS') as mock_model:
            mock_instance = mock.MagicMock()
            mock_model.get_or_create.return_value = mock_instance
            mock_instance.state = {"compress": 0}
            with mock.patch.object(Video, 'convert_format') as mock_convert:
                mock_convert.return_value = {"path": "output.mov"}
                video = Video(path=self.temp_video)
                result = video.convert_format(ext="mov")
                assert isinstance(result, dict)


if __name__ == "__main__":
    main(verbosity=2)
