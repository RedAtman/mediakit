import os
import subprocess
import copy

from utils import translate
from config import config

ret = {k: getattr(config, k) for k in dir(config) if k.isupper()}
print('config', config, ret)


# 执行命令
# assert False, '断言暂停执行代码'

# 输入视频路径
# video_path_org = input(':').strip()

# 视频路径
video_path_org = 'tmp/input.mp4'
video_path_org = '/Users/nut/Movies/Theater/Time-lapse/20190609 冰山梁.mp4'
# video_path_org = '20190609 冰山梁.mp4'

# 获取视频文件格式
file_format = video_path_org.split('.')[-1]

# 生成临时文件及新文件路径
tmp = 'tmp/tmp' + '.' + file_format
media_path_new = 'media/' + video_path_org.split('/')[-1]
# print(media_path_new)

# 背景声音路径
audio_path_org = '/Users/nut/Downloads/Highland.m4a'
# 背景声音延时秒数
audio_defer = '162.8'

# 视频元数据
title = media_path_new.split('.')[0]
keywords = {
    "time_lapse": ["延时摄影", "风光摄影", "延时", "摄影", "风景", "风光"],
    "camera": ["Sony", "a3600", "α3600", "SONY-A3600", "SONY-α3600", "APS-C", "半幅", "半画幅", "残幅"],
    "lens": ["Sigma", "适马", "16mm", "F1.4", "16mm F1.4"],
    "specific": ["白云", "蓝天", "天空", "山顶", "自驾游", "驾车", "冰山梁"],
}
author = ["aQuantum", "一枚量子"]


def generate_metadat(title='一枚量子的延时摄影作品', keywords=[], author=['一枚量子']):
    '''
    doc: 生成视频元数据;
    :params
        title: string, 视频标题;
        keywords: dict{key:list} / list, 视频关键词;
        author: list, 视频作者;
    '''
    metadata = []
    metadata.extend(['-metadata', 'title=' + title])
    metadata.extend(['-metadata', 'author=' + " ".join(author)])

    # 若是dict 则拼接values
    if type(keywords) is dict:
        from functools import reduce

        def concat(a, b):
            # print(type(a),type(b))
            a.extend(b)
            return a

        keywords_concat = reduce(concat, list(keywords.values()))

        keywords_en = translate.result(keywords_concat)

        keywords_concat.extend(keywords_en)

        # print('keywords_concat', keywords_concat)

        metadata.extend(
            ['-metadata', 'keywords=TimeLapse Time-Lapse timelapse ' + " ".join(keywords_concat)])
        return metadata

    metadata.extend(['-metadata', 'author=' + " ".join(author)])
    return metadata



# 生成元数据
metadata = generate_metadat(
    title='一枚量子的延时摄影作品', keywords=keywords, author=author)

metadata = ['-metadata', 'author=' + "@@@ "]
# print('metadata', metadata)


# 执行命令
# assert False, '断言暂停执行代码'

order_prefix = ['ffmpeg', '-y', '-loglevel', 'error']
try:

    # 视频文件静音命令
    order = copy.deepcopy(order_prefix)
    order.extend(['-i', video_path_org])
    order.extend(metadata)
    order.extend(['-an',
                  '-c:v', 'copy',
                  tmp])

    # retcode = subprocess.run(order)
    retcode = subprocess.call(order)
    # retcode = subprocess.check_call(order)
    # retcode = subprocess.check_output(order)

except Exception as e:
    print('捕捉到异常：' + e)
    raise
else:

    order = copy.deepcopy(order_prefix)
    order.extend(['-i', tmp,
                  '-ss', audio_defer,
                  '-i', audio_path_org,
                  'afade=t=in:ss=0:d=15',
                  # '-filter_complex',
                  # "[1:a]afade=t=in:ss=0:d=5[a1]",
                  '-c', 'copy',
                  '-shortest',
                  media_path_new])
    retcode = subprocess.run(order)
    print('任务已完成！')
    pass

finally:
    order = copy.deepcopy(order_prefix)
    order.extend(['-i', media_path_new,
                  '-f', 'ffmetadata', 'tmp/METADATA.txt'])
    retcode = subprocess.call(order)
    print(retcode)
    pass
