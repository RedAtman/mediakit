# import re

# path = '/Users/nut/Downloads/Highland.m4a'
# regex = '([^<>/\\\|:""\*\?]+)\.\w+$'
# regex = '(.*)\/([^<>/\\\|:""\*\?]+)\.(\w+)$'
# ret = re.findall(regex, path)

# print('ret', type(ret), ret)


import os
import subprocess
import copy

from utils import Media, translate
from config import config

artist = config.ARTIST
category = config.CATEGORY.get("time_lapse")
camera = config.CAMERA.get("sony_α3600")
lens = config.LENS.get("sigma_16mm_f1.4")
camera = config.CAMERA.get("sony_α7r2")
lens = config.LENS.get("laowa_12mm_f2.4")
keywords = ['鸟巢', '国家体育馆']
path = '/Users/nut/Movies/Theater/tmp/2.mp4'
path = '/Users/nut/Pictures/Resource/preset/20200520_01_H265-444_1080p_25_UHQ_mb05.mov'
# path = '/Users/nut/Movies/Resource/C0007.MP4'
# 耗时 37.80306315422058
media = Media(path, artist=artist, category=category,
              camera=camera, lens=lens, keywords=keywords)
# ret = media.decode(format='mov')
# ret = media.trim_path
# ret = media.trim(ss="00:00:24", to="00:01:24")
# times = (("00:05:02", "00:05:42"), ("00:12:45",
#                                     "00:18:48"), ("00:20:10", "00:22:50"), ("00:26:56", "00:28:36"))
# ret = media.trim_mul(times=times)
# ret = media.duration
# ret = media.delete_voice()
# ret = media.dir
# ret = media.order_metadata
ret = media.metadata
# ret = media.keywords_list
ret = media.save_metadata()
# ret = media.set_metadata()
# ret = media.add_voice('/Users/nut/Downloads/Sun and Stars.m4a', '79.9')
# ret = media.images_to_video('/Users/nut/Pictures/Resource/preset/20200510 鸟巢', 'jpg', bit_rate="10000k")
# data = ["time lapse 2019 1920*1080", "aQuantum", "一枚量子", "aQuantum", "一枚量子", "延时摄影", "风光摄影", "延时", "摄影", "风景", "风光", "TimeLapse", "Time-Lapse", "timelapse", "Sony", "a3600", "α3600", "SONY-A3600", "SONY-α3600", "APS-C", "半幅", "半画幅", "残幅", "Sigma", "适马", "16mm", "F1.4", "16mm F1.4", "呵呵哒"]
# data = ["time lapse 2019 (1920*1080)","半幅", "半画幅", "残幅", "Sigma", "适马", "16mm", "F1.4", "16mm F1.4", "呵呵哒"]
# print('translate',translate,translate.result(data))

print('media', ret)
