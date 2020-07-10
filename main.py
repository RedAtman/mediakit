from core import init
from utils import log, Media

# path = '/Users/nut/Downloads/RS/COAT1408.mp4'
# media = Media(path,loglevel='info')

files = [
    {
        'path':'/Users/nut/Downloads/RS/COAT1444.mp4',
        'trim_times':(
            ("00:50:22", "01:03:27"),
            ("01:19:39", "01:37:04"),
            # ("02:05:29", "02:36:40"),
            # ("00:26:56", "00:28:36")
        )
    },
    {
        'path':'/Users/nut/Downloads/RS/Coat – CK CYBER RANKING 2019 – CTO554-B.mp4',
        'trim_times':(
            ("00:00:00", "02:15:30"),
            ("02:44:51", "99:37:04"),
            # ("02:05:29", "02:36:40"),
            # ("00:26:56", "00:28:36")
        )
    },
]
# files = [
#     {
#         'path':'/Users/nut/Downloads/RS/COAT1444.mp4',
#         'trim_times':(
#             ("00:00:00", "00:00:10"),
#             ("00:01:00", "00:01:10"),
#             # ("02:05:29", "02:36:40"),
#             # ("00:26:56", "00:28:36")
#         )
#     },
#     {
#         'path':'/Users/nut/Downloads/RS/Coat – CK CYBER RANKING 2019 – CTO554-B.mp4',
#         'trim_times':(
#             ("00:00:00", "00:00:10"),
#             ("00:01:00", "00:01:10"),
#             # ("02:05:29", "02:36:40"),
#             # ("00:26:56", "00:28:36")
#         )
#     },
# ]

ret = Media.trim_mul_file(files=files)
# ret = media.trim_path
log.info('ret', ret)
