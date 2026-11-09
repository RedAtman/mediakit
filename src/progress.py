"""Progress that writes the DB state, as opposed to the display-only progress bars.

Lives in src/ rather than utils/ because it is the one progress implementation
that needs the ORM model: utils/progress.py is a rendering library and should not
depend on src.models. Same reason base/media.py keeps the two apart when it builds
progress_list (TqdmProgress from utils, this from src).
"""

from src.models import Media
from utils.progress import BaseProgress

__all__ = ['MediaStateProgress']


class MediaStateProgress(BaseProgress):
    def __init__(self, total: int, model: Media):
        super().__init__(total)
        self.model = model

    def __after_percent_step__(self):
        self.run()

    def run(self):
        # percent = 当前帧 / 源帧数; 而 compress 会强制 -r 24, 低帧率源(如 10fps 延时)
        # 的输出帧数会超过分母, 算出 >1 的比值. 这里夹到 [0,1] 而不是让
        # State.compress (ge=-2, le=2) 抛 ValidationError 把整次压缩弄挂.
        self.model.update_state('compress', min(self.percent, 1.0))
