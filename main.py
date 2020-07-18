import sys,os,threading
from core import init
from utils import log, Log, Media, BoundedExecutor, decorator
# print(log._Log__level_mapping)
# print(log._Log__level_list)
# print(log.level)
# log.level = 'warning'
# print(log.level)
# print(log.logger)

# path = '/Users/nut/Downloads/RS/1408.mp4'
# media = Media(path,loglevel='info')
# media.transcode()

files = [
    # {
    #     'path':'/Users/nut/Downloads/RS/ANV131.mp4',
    #     'trim_times':(
    #         ("00:00:00", "00:00:56"),
    #         ("00:10:00", "00:10:56"),
    #         ("00:20:00", "00:20:56"),
    #         ("00:30:00", "00:30:56"),
    #         ("00:40:00", "00:40:56"),
    #         ("00:50:00", "00:50:56"),
    #         ("01:00:00", "01:00:56"),
    #         ("01:10:00", "01:10:56"),
    #         ("01:20:00", "01:20:56"),
    #         ("00:00:00", "00:00:56"),
    #         ("00:10:00", "00:10:56"),
    #         ("00:20:00", "00:20:56"),
    #         ("00:30:00", "00:30:56"),
    #         ("00:40:00", "00:40:56"),
    #         ("00:50:00", "00:50:56"),
    #         ("01:00:00", "01:00:56"),
    #         ("01:10:00", "01:10:56"),
    #         ("01:20:00", "01:20:56"),
    #     )
    # },
    {
        'path':'/Users/nut/Downloads/RS/VDGBNG0003.mp4',
        'trim_times':(
            ("00:00:00", "00:00:06"),
            ("00:10:00", "00:10:16"),
            # ("00:20:00", "00:20:56"),
            # ("00:30:00", "00:30:56"),
            # ("00:40:00", "00:40:56"),
            # ("00:50:00", "00:50:56"),
            # ("01:00:00", "01:00:56"),
            # ("01:10:00", "01:10:56"),
            # ("01:20:00", "01:20:56"),
            # ("00:00:00", "00:00:56"),
            # ("00:10:00", "00:10:56"),
            # ("00:20:00", "00:20:56"),
            # ("00:30:00", "00:30:56"),
            # ("00:40:00", "00:40:56"),
            # ("00:50:00", "00:50:56"),
            # ("01:00:00", "01:00:56"),
            # ("01:10:00", "01:10:56"),
            # ("01:20:00", "01:20:56"),
        )
    },
    # {
    #     'path':'/Users/nut/Downloads/RS/[g@mes ura] PEEPING STRAIGHT FUCK EX – OOTORI (ノンケ激盗撮EX・鳳) [UGS63].wmv',
    #     'trim_times':(
    #         ("02:27:31", "02:57:56"),
    #     )
    # },
]

# <INFO> media.py[26][26] 耗时, 437.49915409088135,

# <INFO> media.py[26][26] 耗时, 236.44972109794617,'-threads', '4',

# <INFO> media.py[26][26] 耗时, 338.2764799594879,

# <INFO> media.py[26][26] 耗时, 320.07262897491455, '-threads', '40',

# ret = Media.muti_trim_compress(files=files)
ret = Media.muti_trim(files=files, callback_list=['compress'])

# media = Media('/Users/nut/Downloads/RS/test.mp4')
# ret = media.trim(time=("00:00:00", "00:00:26"))

# ret = Media.compress(file_path = '/Users/nut/Downloads/RS/test.mp4')

log.info('ret', ret)

@decorator.timekeep
def main():
    executor = BoundedExecutor(20, 20)

    for file in files:
        suffix_number = 0
        trim_times = file.get('trim_times')
        for time in trim_times:
            obj = Media(file.get('path'))
            suffix_number += 1
            executor.submit(obj.trim, time=time,suffix_number=suffix_number)
            # task = cls.__thread_pool.submit(
            #     obj.trim, time=time,suffix_number=suffix_number)
            # # task.add_done_callback(callback)
            log.info('muti_trim_compress',time,suffix_number)
        executor.shutdown(wait=True)

    # cls.__thread_pool.shutdown(wait=True)
    log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().name, os.getpid()))


if __name__ == '__main__':
    # main()
    pass


