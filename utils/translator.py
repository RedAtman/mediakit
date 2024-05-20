import hashlib
from itertools import chain
import json
import logging
from typing import Any, List, Set, Tuple, Union

import requests

from config import CONFIG


logger = logging.getLogger()


class Translator:
    """百度通用翻译接口封装类。
    e.g.
    >>> from utils import Translator
    >>> translator = Translator()
    >>> translator.result('白云')
    ['White clouds']
    """

    if not all(
        [
            CONFIG.BAIDU_TRANSLATE_API,
            CONFIG.BAIDU_TRANSLATE_APP_ID,
            CONFIG.BAIDU_TRANSLATE_SECRET_KEY,
            CONFIG.BAIDU_TRANSLATE_SALT,
        ]
    ):
        raise ValueError(
            "Please set BAIDU_TRANSLATE_API, BAIDU_TRANSLATE_APP_ID, BAIDU_TRANSLATE_SECRET_KEY, BAIDU_TRANSLATE_SALT in config.py"
        )

    @classmethod
    def sign(cls, q: str):
        """生成百度翻译api要求的sign(md5值)。
        :param q: :String: 待翻译文字。
        :return :String: 已翻译文字。
        """
        sign = CONFIG.BAIDU_TRANSLATE_APP_ID + q + CONFIG.BAIDU_TRANSLATE_SALT + CONFIG.BAIDU_TRANSLATE_SECRET_KEY
        return hashlib.md5(sign.encode()).hexdigest()

    @classmethod
    def translate(cls, text: Union[Any, List, Set, Tuple]) -> Any:
        """发送翻译请求、解析翻译结果。输入默认检测语种，输出英文。
        :param: text(String & List & Set): 待翻译文字。
        :return(List): 已翻译文字。
        """
        if isinstance(text, (list, tuple, set)):
            text = ",".join(text)

        if not isinstance(text, str):
            raise TypeError("text must be str, list or set")

        data = {
            "q": text,
            "from": "auto",
            "to": "en",
            "appid": CONFIG.BAIDU_TRANSLATE_APP_ID,
            "salt": CONFIG.BAIDU_TRANSLATE_SALT,
            "sign": cls.sign(text),
        }

        # 获取翻译结果
        repose = requests.post(CONFIG.BAIDU_TRANSLATE_API, data=data, timeout=10)
        content = repose.json()
        trans_result = content.get("trans_result", [])
        _ = [val.get("dst", "").split(", ") for val in trans_result]

        result = None
        try:
            result = json.loads(json.dumps(_))
            result = list(chain(*result))
        except ValueError as err:
            logger.exception(err)
            raise err
        return result
