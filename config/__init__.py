import os
import importlib
from config import g, user


class Config:
    def __init__(self):
        '''
        构造配置对象，含：全局配置、用户配置。
        '''

        # 1. 获取默认全局配置g文件内大写属性
        for attr in dir(g):
            # 若属性为大写
            if attr.isupper():
                # 设置 self 对象内的 attr 属性的值为 g 内的 attr
                # 即 config对象内的DEBUG属性为g的DEBUG
                # print(attr, getattr(g, attr))
                setattr(self, attr, getattr(g, attr))

        # 2. 获取用户文件内的属性放入对象内，对默认属性进行覆盖
        # config_user = os.environ.get('config_user')
        # print('config_user', config_user)
        # config_user = importlib.import_module(config_user)
        # print('config_user', config_user)

        for attr in dir(user):
            # print('attr', attr)
            if attr.isupper():
                setattr(self, attr, getattr(user, attr))


# 实例化对象 用于执行文件调用
config = Config()
