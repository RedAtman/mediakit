import hashlib
import http.client
import json
import random
import urllib


class BaiduTranslator:
    def __init__(self, appid, secretKey):
        self.appid = appid
        self.secretKey = secretKey
        self.httpClient = None
        self.api = "/api/trans/vip/translate"

    def translate(self, q: str, fromLang="auto", toLang="en"):
        salt = random.randint(32768, 65536)
        sign: str = self.appid + q + str(salt) + self.secretKey
        sign = hashlib.md5(sign.encode()).hexdigest()
        url = (
            self.api
            + "?appid="
            + self.appid
            + "&q="
            + urllib.parse.quote(q)
            + "&from="
            + fromLang
            + "&to="
            + toLang
            + "&salt="
            + str(salt)
            + "&sign="
            + sign
        )

        try:
            self.httpClient = http.client.HTTPConnection("api.fanyi.baidu.com")
            self.httpClient.request("GET", url)

            # response是HTTPResponse对象
            response = self.httpClient.getresponse()
            result_all = response.read().decode("utf-8")
            result = json.loads(result_all)

            return result
        except Exception as e:
            print(e)
        finally:
            if self.httpClient:
                self.httpClient.close()


if __name__ == "__main__":
    import os
    appid = os.environ.get("BAIDU_TRANSLATE_APP_ID")
    secretKey = os.environ.get("BAIDU_TRANSLATE_SECRET_KEY")
    translator = BaiduTranslator(appid, secretKey)
    print(translator.translate("苹果"))
