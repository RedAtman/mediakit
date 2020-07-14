import json
from utils import Media, translate
from config import config

media = Media('/Users/nut/Downloads/RS/test.mp4  ')

# ret = media.metadata
# ret = media.save_metadata()
# ret = media.duration
ret = media.compress()

# print(
#     type(ret),
#     ret,
#     dir(ret),
#     # ret.args,
#     # ret.check_returncode(),3
#     # ret.returncode,
#     # ret.stderr,
#     # ret.stdout
#     )

# ret = json.loads(ret)

print(
    type(ret),
    ret,
    # dir(ret),
    # ret.args,
    # ret.check_returncode(),
    # ret.returncode,
    # ret.stderr,
    # ret.stdout
    )
# print(640*360/800)
# print(1280*720/1400)
# print(1280*720/1400)