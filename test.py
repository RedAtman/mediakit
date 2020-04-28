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

# path = '/Users/nut/Movies/Theater/tmp/2.mp4'
# path = '/Users/nut/Movies/Theater/tmp/images/output.avi'
# path = '/Users/nut/Movies/Theater/Time-lapse/20190609 冰山梁.mp4'
path = '/Users/nut/Movies/Theater/tmp/2.mp4'
# path = '/Users/nut/Movies/Theater/tmp/2_delete_voice.mp4'
media = Media(path)
# ret = media.duration
# ret = media.delete_voice()
# ret = media.metadata()
# ret = media.save_metadata()
# ret = media.add_voice('/Users/nut/Downloads/Highland.m4a', '162.8')
ret = media.images_to_video('/Users/nut/Movies/Theater/tmp/imges', 'jpg')

print('media', ret)
