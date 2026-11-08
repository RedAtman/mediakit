import logging
from unittest import TestCase, mock

from config import CONFIG
from utils.translator import Translator

logger = logging.getLogger()


class TestTranslator(TestCase):
    def test_missing_credentials_raises(self):
        with mock.patch.object(CONFIG, 'BAIDU_TRANSLATE_SECRET_KEY', ''):
            with self.assertRaises(ValueError):
                Translator._require_config()

    @mock.patch('utils.translator.requests.post')
    def test_translate_sends_joined_text_and_flattens_response(self, mock_post):
        mock_post.return_value.json.return_value = {'trans_result': [{'dst': 'White clouds'}, {'dst': 'blue sky, sky'}]}
        # 只打桩配置校验和 HTTP: 拼接/拍平逻辑跑真的
        with mock.patch.object(Translator, '_require_config', return_value=None):
            result = Translator.translate(['白云', '蓝天'])

        self.assertEqual(result, ['White clouds', 'blue sky', 'sky'])
        self.assertEqual(
            mock_post.call_args.kwargs['data'],
            {
                'q': '白云,蓝天',
                'from': 'auto',
                'to': 'en',
                'appid': CONFIG.BAIDU_TRANSLATE_APP_ID,
                'salt': CONFIG.BAIDU_TRANSLATE_SALT,
                'sign': Translator.sign('白云,蓝天'),
            },
        )
        self.assertEqual(mock_post.call_args.kwargs['timeout'], 10)

    def test_unsupported_type_raises(self):
        with mock.patch.object(Translator, '_require_config', return_value=None):
            with self.assertRaises(TypeError):
                Translator.translate(123)  # type: ignore[arg-type]
