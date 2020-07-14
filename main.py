from core import init
from utils import log, Media

# path = '/Users/nut/Downloads/RS/1408.mp4'
# media = Media(path,loglevel='info')
# media.transcode()

files = [
    {
        'path':'/Users/nut/Downloads/RS/ANV131.mp4',
        'trim_times':(
            ("00:00:00", "00:00:26"),
            ("00:10:00", "00:10:26"),
        )
    },
    # {
    #     'path':'/Users/nut/Downloads/RS/ccav-A.mp4',
    #     'trim_times':(
    #         # ("00:00:00", "01:29:30"),
    #         ("02:34:13", "99:37:04"),
    #     )
    # },
]

# <INFO> media.py[26][26] 耗时, 437.49915409088135,

# <INFO> media.py[26][26] 耗时, 236.44972109794617,'-threads', '4',

# <INFO> media.py[26][26] 耗时, 338.2764799594879,

# <INFO> media.py[26][26] 耗时, 320.07262897491455, '-threads', '40',
# ret = media.trim_path
# ret = Media.trim_mul_file(files=files)

media = Media('/Users/nut/Downloads/RS/ANV131.mp4')
ret = media.trim(time=("00:00:00", "00:00:26"))
log.info('ret', ret)
