import sys,os,threading
from core import init
from utils import log, Log, Media, BoundedExecutor, decorator
from tmp.files import files
# print(log._Log__level_mapping)
# print(log._Log__level_list)
# print(log.level)
log.level = 'warning'
# print(log.level)
# print(log.logger)


# path = '/Users/nut/Downloads/RS/1408.mp4'
# media = Media(path,loglevel='info')
# media.transcode()


# media = Media('/Users/nut/Downloads/RS/test.mp4')
# ret = media.trim(time=("00:00:00", "00:00:26"))


ret = Media.muti_trim(files=files, callback_list=['compress'])


# ret = Media.compress(file_path = '/Users/nut/Downloads/RS/test.mp4')


log.info('ret', ret)


if __name__ == '__main__':
    # main()
    pass


