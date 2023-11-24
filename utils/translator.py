import hashlib
import json
from itertools import chain

import requests

from config import config
from logger import logger


class Translator:
    """ 百度通用翻译接口封装类。
    e.g.
    >>> from utils import Translator
    >>> translator = Translator()
    >>> translator.result('白云')
    ['White clouds']
    """
    if not all([
        config.BAIDU_TRANSLATE_API,
        config.BAIDU_TRANSLATE_APP_ID,
        config.BAIDU_TRANSLATE_SECRET_KEY,
        config.BAIDU_TRANSLATE_SALT,
    ]):
        logger.info(
            'Translator api %s, %s, %s, %s',
            config.BAIDU_TRANSLATE_API,
            config.BAIDU_TRANSLATE_APP_ID,
            config.BAIDU_TRANSLATE_SECRET_KEY,
            config.BAIDU_TRANSLATE_SALT
        )
        raise ValueError('请在环境变量中配置百度翻译api')

    @classmethod
    def sign(cls, q):
        """ 生成百度翻译api要求的sign(md5值)。
        :param q: :String: 待翻译文字。
        :return :String: 已翻译文字。
        """
        sign = config.BAIDU_TRANSLATE_APP_ID + q + \
            config.BAIDU_TRANSLATE_SALT + config.BAIDU_TRANSLATE_SECRET_KEY
        return hashlib.md5(sign.encode()).hexdigest()

    @classmethod
    def translate(cls, text):
        """ 发送翻译请求、解析翻译结果。输入默认检测语种，输出英文。
        :param: text(String & List & Set): 待翻译文字。
        :return(List): 已翻译文字。
        """
        if isinstance(text, (list, tuple, set)):
            text = ','.join(text)

        if not isinstance(text, str):
            raise TypeError('text must be str, list or set')

        data = {
            'q': text,
            'from': 'auto',
            'to': 'en',
            'appid': config.BAIDU_TRANSLATE_APP_ID,
            'salt': config.BAIDU_TRANSLATE_SALT,
            'sign': cls.sign(text),
        }

        # 获取翻译结果
        repose = requests.post(config.BAIDU_TRANSLATE_API, data=data, timeout=10)
        logger.info('%s %s %s %s', 'requests', data,
                    type(repose.content), repose)
        content = repose.json()
        trans_result = content.get('trans_result', [])
        _ = [val.get('dst', '').split(', ') for val in trans_result]
        # logger.debug('trans_result %s %s', type(trans_result), trans_result)

        result = None
        try:
            result = json.loads(json.dumps(_))
            result = list(chain(*result))
        except ValueError as err:
            logger.exception('不能进行json.loads处理: %s', err)
            result = trans_result
        logger.info('Translate result result %s %s', type(result), result)
        return result
