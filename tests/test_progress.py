import logging
from unittest import TestCase, mock

from src.progress import MediaStateProgress

logger = logging.getLogger()


class TestMediaStateProgress(TestCase):
    def _written_values(self, total: int, current: int):
        """设 current 时 BaseProgress 的 hook 会自动触发 run(), 不要再手动调一次."""
        model = mock.MagicMock()
        progress = MediaStateProgress(total=total, model=model)
        progress.current = current
        return [call.args[1] for call in model.update_state.call_args_list]

    def test_percent_above_one_is_clamped(self):
        """compress 强制 -r 24, 低帧率源的输出帧数会超过源帧数这个分母.

        percent 于是可能 > 1 (10 帧源打出 24 帧 = 2.4), 而 State.compress 的约束是
        ge=-2/le=2, 直接写进去会让 pydantic 抛 ValidationError 把整次压缩弄挂.
        """
        written = self._written_values(total=10, current=24)

        self.assertTrue(written)
        self.assertEqual(max(written), 1.0)

    def test_normal_progress_is_passed_through(self):
        written = self._written_values(total=10, current=5)

        self.assertEqual(written[-1], 0.5)
