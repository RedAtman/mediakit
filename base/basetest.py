from enum import Enum
import functools
import json
import logging
import os
import sys
import traceback
from unittest import TestCase
import urllib
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv, set_key


# from django.test import TestCase

logger = logging.getLogger()


# Response = type(
#     "Response",
#     (DictObj,),
#     {
#         "status": 0,
#         "data": {},
#     },
# )

from utils.response import Response


classproperty = type(
    "classproperty",
    (property,),
    {"__get__": lambda self, cls, owner: self.fget.__get__(None, owner)()},
)


class DictObj(dict):
    def __init__(self, in_dict: dict):
        assert isinstance(in_dict, dict)
        for key, val in in_dict.items():
            if isinstance(val, (list, tuple)):
                setattr(
                    self, key, [DictObj(x) if isinstance(x, dict) else x for x in val]
                )
            else:
                setattr(self, key, DictObj(val) if isinstance(val, dict) else val)


class AssertWrap(type):
    def __new__(cls, name, bases, attr__map):
        for attr in attr__map:
            if hasattr(attr__map[attr], "__call__") and attr.startswith("test_"):
                attr__map[attr] = cls.wrap(attr__map[attr])
        return type.__new__(cls, name, bases, attr__map)

    # @staticmethod
    # def assert_response(schemer, response):
    #     assert response.status >= 200 and response.status < 300, \
    #         f'{response.status}, {response.data}'
    #     schemer.validate(response.data)
    #     try:
    #         schemer.validate(response.data)
    #     except SchemaError as err:
    #         raise err
    #         # raise ApiInputException(101, f'输入数据不合法: msg: {err}')

    @staticmethod
    def assert_response(response):
        assert (
            response.status >= 200 and response.status < 300
        ), f"{response.status}, {response.data}"
        assert getattr(response, "data", None) is not None, "response.data is None"
        assert isinstance(
            response.data, (dict, list)
        ), "response.data is not dict or list"

    # @staticmethod
    # def assert_data(data):
    #     assert isinstance(data, dict), 'response.data is not dict'

    @classmethod
    def wrap(cls, f):
        @functools.wraps(f)
        def func(self, *args, **kwargs):
            try:
                response = f(self, *args, **kwargs)
                # logger.info(schema)
                # schemer = self.check_schema(schema)
                cls.assert_response(response)
                # cls.assert_data(response.data)
                return response
            except Exception as err:
                f_back = sys._getframe().f_back
                logger.info(
                    {
                        "__qualname__": f.__qualname__,
                        "args": args,
                        "kwargs": kwargs,
                        "caller": "%s:%s:%s"
                        % (
                            f_back.f_code.co_filename,
                            f_back.f_lineno,
                            f_back.f_code.co_name,
                        ),
                        "err": err,
                        # 'traceback': traceback.format_exc(),
                    }
                )
                raise err

        return func


class BaseTest(TestCase, metaclass=AssertWrap):
    env_file_name = ".env"
    env_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), env_file_name
    )
    load_dotenv(env_file)
    ENV_NAME = os.getenv("ENV_NAME")
    TOKEN_KEY = "JMS_TOKEN"
    default_headers = {
        "Content-Type": "application/json",
    }
    mapping__env = {
        "dev": {
            "base_url": "http://127.0.0.1:8080",
            "api": "/api/v1",
            "token": "",
            "username": "admin",
            "password": "111111",
            # 'password': getpass.getpass("Please input your password:"),
        },
        "test": {
            "base_url": "https://test.dev.local",
            "api": "",
            "token": "",
            "username": "",
            "password": "",
        },
        "prod": {
            "base_url": "",
            "api": "",
            "token": "",
        },
    }

    schema = None
    env = classproperty(
        classmethod(lambda cls: DictObj(cls.mapping__env.get(cls.ENV_NAME, {})))
    )
    headers = classproperty(
        classmethod(lambda cls: dict(cls.default_headers, **cls.auth_headers))
    )
    url = classmethod(lambda cls, url: cls.env.base_url + url)
    api = classmethod(lambda cls, api: cls.env.base_url + cls.env.api + api)
    auth_headers = classproperty(
        classmethod(
            lambda cls: {
                "Authorization": f"Bearer {cls.token}",
                # 'Cookie': 'SESSION_COOKIE_NAME_PREFIX=jms_',
            }
        )
    )

    class MethodChoices(Enum):
        GET = "GET"
        POST = "POST"

    @staticmethod
    def check_schema(schema):
        if schema is None:
            raise Exception("schema is None, please set schema in testCase")
        schema = Schema(schema)
        return schema

    @classmethod
    def refresh_token(cls):
        response = cls.login()
        token = response.data.get("token")
        if token is None:
            raise Exception("token is None")
        set_key(cls.env_file, cls.TOKEN_KEY, token)
        load_dotenv(cls.env_file)

    @classproperty
    @classmethod
    def token(cls):
        token = os.getenv(cls.TOKEN_KEY)
        if not token:
            cls.refresh_token()
            token = os.getenv(cls.TOKEN_KEY)
        return token

    @staticmethod
    def parse(response):
        try:
            data = json.loads(response.read().decode("utf-8"))
        except Exception as err:
            logger.error(
                {
                    "msg": "response parse error",
                    "error": err,
                }
            )
            data = {}
        setattr(response, "data", data)

    @classmethod
    def _request(
        cls,
        url: str = "",
        api: str = "",
        method="GET",
        headers: dict = {},
        data: dict = {},
    ):
        if url:
            url = cls.url(url)
        elif api:
            url = cls.api(api)
        else:
            raise Exception("url & api must be specified")

        if method.upper() == "GET":
            # url = '?' + urllib.parse.urlencode({url}, data=bytes(json.dumps(data), encoding="utf-8"))
            # data = urllib.parse.urlencode(data)
            url += "?" + urllib.parse.urlencode(data)
            data = None
        elif method.upper() == "POST":
            # data = urllib.parse.urlencode(data).encode('utf-8')
            data = json.dumps(data).encode("utf-8")
        else:
            raise Exception("method must be GET or POST")

        headers = headers or cls.headers

        try:
            request = urllib.request.Request(
                url, data=data, headers=headers, method=method
            )
            response = urllib.request.urlopen(request)
        # except ConnectionRefusedError as err:
        except urllib.error.HTTPError as err:
            logger.info(err.__dict__)
            if err.code == 401:
                return Response(err.code, err)
            raise err
        except urllib.error.URLError as err:
            logger.info(err.__dict__)
            if isinstance(err.reason, ConnectionRefusedError):
                raise Exception(
                    f'Please check {os.getenv("DJANGO_PROJECT")}: {cls.ENV_NAME} server is running'
                )
            return Response(
                500,
                err,
                data={
                    # 'url': err.url,
                    "msg": f"{cls.ENV_NAME} Server error: {err}",
                    # 'error': _response.info(),
                    "traceback": traceback.format_exc(),
                },
            )
        if response.status >= 200 and response.status < 400:
            cls.parse(response)
            logger.info(response.data)
        else:
            logger.info(("response.__dict__", response.__dict__))
        return response

    @classmethod
    def request(cls, *args, **kwargs):
        response = cls._request(*args, **kwargs)
        # return response
        if response.status == 401:
            cls.refresh_token()
            response = cls._request(*args, **kwargs)
        return response

    @classmethod
    def login(cls):
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")
        if not username or not password:
            raise Exception(
                f"Please set USERNAME and PASSWORD in {cls.env_file_name} file"
            )
        response = cls.request(
            api="/authentication/tokens/",
            method="POST",
            headers=cls.default_headers,
            data={
                "username": username,
                "password": password,
            },
        )
        return response

    def test_login(self):
        # python apps/manage.py test apps.common.basetest.BaseTest.test_login
        response = self.login()
        self.assertIsInstance(response.data.get("token"), str)
        return response


class ExampleTest(BaseTest):

    def test_health(self):
        # python apps/manage.py test apps.common.basetest.ExampleTest.test_health
        response = self.request(url="/api/health/", method="GET", data={})
        self.assertEqual(response.data.get("status"), True)
        self.assertEqual(response.data.get("db_status"), True)
        self.assertEqual(response.data.get("redis_status"), True)
        self.assertIsInstance(response.data.get("api_time"), float)
        return response

    def test_users_profile(self):
        # python apps/manage.py test apps.common.basetest.ExampleTest.test_users_profile
        response = self.request(api="/users/profile/", method="GET", data={})
        self.assertIsInstance(response.data.get("id"), str)
        self.assertEqual(len(response.data.get("id")), 36)
        return response


if __name__ == "__main__":

    # example = ExampleTest()
    # example.test_login()
    # example.test_health()
    # example.test_users_profile()

    _dict = {
        "a": "-" * 100,
        "b": 2,
        "c": {
            "d": 3,
            "e": 4,
            "f": {
                "g": 5,
                "h": 6,
            },
        },
    }
    logger.info(_dict)
