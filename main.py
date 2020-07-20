import sys,os,threading
from core import init
from utils import log, Log, Media, BoundedExecutor, decorator
from tmp.files import files
# log.info('test')
# print(log._Log__level_mapping)
# print(log._Log__level_list)
# print(log.level)
log.level = 'warning'
# print(log.level)
# print(log.logger)


# path = '/Users/nut/Downloads/RS/1408.mp4'
# media = Media(path,loglevel='info')
# media.transcode()


# media = Media('/Users/nut/Downloads/RS/_test/test.mp4')
# ret = media.trim(time=("00:00:00", "00:00:26"))
# media = Media('/Users/nut/Downloads/RS/_to_be_compress/BelAmi Online – Jambo Africa Series – Hoyt Kogan &amp;amp; Jarrod Lanvin – 810p.mp4')

# ret = media.metadata.get('format').get('width')




# ret = Media.multi_trim(files=files, callback_list=['compress'])
# ret = Media.multi_trim(files=files)


# ret = Media.compress(file_path = '/Users/nut/Downloads/RS/_test/test.mp4')
# ret = Media.compress(file_path = '/Users/nut/Downloads/RS/_to_be_compress/BelAmi Online – Jambo Africa Series – Hoyt Kogan &amp;amp; Jarrod Lanvin – 810p.mp4')
# ret = Media.get_width('/Users/nut/Downloads/RS/_to_be_compress/BelAmi Online – Jambo Africa Series – Hoyt Kogan &amp;amp; Jarrod Lanvin – 810p.mp4')


ret = Media.multi_compress(path = '/Users/nut/Downloads/RS/_to_be_compress')
# ret = Media.multi_compress(path='/Users/nut/Downloads/RS/_test')


log.warning('ret', ret)


if __name__ == '__main__':
    # main()
    pass


