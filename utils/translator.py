import hashlib
from itertools import chain
import json
import logging
from typing import List, Set, Tuple, Union

import requests

from config import CONFIG


logger = logging.getLogger()


class Translator:
    """Translator class to translate text to English. based on Baidu translate API.
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
        """Generate sign(md5) for Baidu translate API.

        Args:
            q (str): Text to translate.

        Returns:
            str: Sign(md5) for Baidu translate API.
        """
        sign = CONFIG.BAIDU_TRANSLATE_APP_ID + q + CONFIG.BAIDU_TRANSLATE_SALT + CONFIG.BAIDU_TRANSLATE_SECRET_KEY
        return hashlib.md5(sign.encode()).hexdigest()

    @classmethod
    def translate(cls, text: Union[str, List[str], Set[str], Tuple[str, ...]]) -> List[str]:
        """Translate text to target language.

        Args:
            text (Union[str, List[str], Set[str], Tuple[str, ...]): Text to translate.

        Returns:
            List[str]: Translated text.
        """
        if isinstance(text, (list, tuple, set)):
            text = ",".join(text)

        if not isinstance(text, str):
            raise TypeError("text must be str, list, set or tuple.")

        data = {
            "q": text,
            "from": "auto",
            "to": "en",
            "appid": CONFIG.BAIDU_TRANSLATE_APP_ID,
            "salt": CONFIG.BAIDU_TRANSLATE_SALT,
            "sign": cls.sign(text),
        }

        repose = requests.post(CONFIG.BAIDU_TRANSLATE_API, data=data, timeout=10)
        content = repose.json()
        trans_result = content.get("trans_result", [])
        _ = [val.get("dst", "").split(", ") for val in trans_result]

        result = None
        try:
            result_list = json.loads(json.dumps(_))
            result = list(chain(*result_list))
            return result
        except ValueError as err:
            logger.exception(err)
            raise err
