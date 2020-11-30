import sys
import os
import threading
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


# path = '/Users/nut/Pictures/Resource/preset/20200809_01_H265-420_1080p_25_LQ.mov'
# path =
# '/Users/nut/Pictures/Resource/preset/20200809_荇桥_02/20200809_02_H265-420_1080p_25_LQ.mov'
path = '/Volumes/SeagateDrive1t/time_lapse/2020/20200902_景山辑芳亭/20200902_H265-420_1080p_25_LQ.mov'
# path = '/Users/nut/Pictures/Resource/20200902_H265-420_1080p_25_LQ.mov'
# path = '/Users/nut/Pictures/Resource/_trim/20200809_荇桥_02_H265-420_1080p_25_LQ_voice-trim_1.mov'
# path = '/Users/nut/Pictures/Resource/20200809_荇桥_01_H265-420_1080p_25_LQ_reverse_voice.mov'
# path = '/Users/nut/Downloads/RS/_test/test.mp4'
# path = ' /Users/nut/Downloads/video/videoHelper.mp4'
# path = '/Users/nut/Downloads/video/_trim/videoHelper-trim_1.mp4'

audio_path = None
# audio_path = '/Users/nut/Music/网易云音乐/Epic Soul Factory,Cesc Vilà,Fran Soto - Hero Memories.mp3'
audio_path = '/Users/nut/Downloads/R. Armando Morabito,Julie Elven,Claudio Pietronik - Angel 2.0 (feat. Julie Elven & Claudio Pietronik).mp3'
# audio_path = '/Users/nut/Downloads/In the Autumn.m4a'

logo_path = '/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png'


# media = Media(path,loglevel='info')
# media.transcode()


media = Media(path)
# ret = Media.compress(file_path=path)
# ret = media.trim(time=("00:00:00", "00:00:03"))

# ret = media.metadata.get('format').get('width')

# ret = media.reverse()


ret = media.combine(logo_path=logo_path, logo_transparent=0.3, audio_path=audio_path,
                    audio_defer=179.5, fade_duration=1, crop='1080p', crop_y=200, reverse=False,)


# ret = Media.multi_trim(files=files, callback_list=['compress'])
# ret = Media.multi_trim(files=files)


# ret = Media.multi_compress(path='/Users/nut/Downloads/RS/_to_be_compress')
# ret = Media.multi_compress(path='/Volumes/ssd2t/RS/_to_be_compress')
# ret = Media.multi_compress(path='/Volumes/ssd2t/storage/inbox/202006')
# ret = Media.multi_compress(path='/Users/nut/Downloads/RS/_test')

log.warning('ret', ret)


if __name__ == '__main__':
    # main()
    pass
