from unittest import TestCase

from src.file.debounce import DebounceBuffer

CALM_PERIOD = 0.1
MAX_FLUSH_INTERVAL = 60.0


class FakeTimer:
    """记录 (interval, callback) 的假定时器, 只由测试显式推进, 不碰 wall clock.

    状态: pending(已 start 且未 cancel)、cancelled(cancel 落在 start 之后、回调未开始)、
    running(定时器线程已进入回调). running 之后再 cancel 是空操作 -- 这正是
    threading.Timer 的语义, 也是 _flush 与 add 抢锁时 cancel 落空的复现点.
    """

    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.daemon = False
        self.started = False
        self.cancelled = False
        self.running = False
        self.finished = False

    @property
    def pending(self):
        return self.started and not self.cancelled and not self.running and not self.finished

    def start(self):
        self.started = True

    def cancel(self):
        if self.running or self.finished:
            return
        self.cancelled = True

    def enter(self):
        """模拟定时器线程已进入回调并在等锁: 此刻 cancel() 已拦不住它."""
        self.running = True

    def resume(self):
        """让已进入回调的那次执行跑完."""
        try:
            self.function()
        finally:
            self.running = False
            self.finished = True

    def fire(self):
        """按定时器线程的方式触发; 已 cancel/已跑完则什么都不做. 返回是否真的跑了."""
        if not self.pending:
            return False
        self.enter()
        self.resume()
        return True


class FakeTimerFactory:
    def __init__(self):
        self.created = []

    def __call__(self, interval, function):
        timer = FakeTimer(interval, function)
        self.created.append(timer)
        return timer

    def calm_timers(self):
        return [timer for timer in self.created if timer.interval == CALM_PERIOD]

    def pending_calm_timers(self):
        return [timer for timer in self.calm_timers() if timer.pending]

    def max_timers(self):
        return [timer for timer in self.created if timer.interval == MAX_FLUSH_INTERVAL]

    def pending_max_timers(self):
        return [timer for timer in self.max_timers() if timer.pending]

    def last_pending_calm_timer(self):
        pending = self.pending_calm_timers()
        assert len(pending) == 1, f'expected exactly one pending calm timer, got {len(pending)}'
        return pending[0]


class TestDebounceBuffer(TestCase):
    def setUp(self):
        self.flushed = []
        self.timers = FakeTimerFactory()
        self.buffer = DebounceBuffer(
            callback=self._flush_callback,
            calm_period=CALM_PERIOD,
            max_flush_interval=MAX_FLUSH_INTERVAL,
            timer_factory=self.timers,
        )

    def tearDown(self):
        self.buffer.stop()

    def _flush_callback(self, paths):
        self.flushed.append(list(paths))

    def test_add_single_path_then_flush(self):
        self.buffer.add('/tmp/file1.mp4')
        self.assertTrue(self.timers.last_pending_calm_timer().fire())
        self.assertEqual(self.flushed, [['/tmp/file1.mp4']])

    def test_dedup_same_path(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file1.mp4')
        self.assertEqual(len(self.timers.calm_timers()), 3)
        self.timers.last_pending_calm_timer().fire()
        self.assertEqual(self.flushed, [['/tmp/file1.mp4']])

    def test_multiple_paths_batched(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file2.mp4')
        self.buffer.add('/tmp/file3.mp4')
        self.timers.last_pending_calm_timer().fire()
        self.assertEqual(len(self.flushed), 1)
        self.assertCountEqual(self.flushed[0], ['/tmp/file1.mp4', '/tmp/file2.mp4', '/tmp/file3.mp4'])

    def test_burst_resets_timer(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file2.mp4')
        self.buffer.add('/tmp/file3.mp4')

        # 每次 add 都重置计时: 只有最后一个 timer 还活着, 前两个已被 cancel
        first, second, third = self.timers.calm_timers()
        self.assertTrue(first.cancelled)
        self.assertTrue(second.cancelled)
        self.assertTrue(third.pending)
        self.assertFalse(first.fire())
        self.assertFalse(second.fire())
        self.assertEqual(self.flushed, [])

        third.fire()
        self.assertEqual(len(self.flushed), 1)
        self.assertCountEqual(self.flushed[0], ['/tmp/file1.mp4', '/tmp/file2.mp4', '/tmp/file3.mp4'])

    def test_multiple_flush_batches(self):
        self.buffer.add('/tmp/file1.mp4')
        self.timers.last_pending_calm_timer().fire()
        self.buffer.add('/tmp/file2.mp4')
        self.timers.last_pending_calm_timer().fire()
        self.assertEqual(self.flushed, [['/tmp/file1.mp4'], ['/tmp/file2.mp4']])

    def test_max_flush_interval(self):
        # 假定时器不会自动开火, 谁先触发完全由测试决定, 所以这里先走 max timer 这条路径
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file2.mp4')
        self.assertEqual(len(self.timers.max_timers()), 1, 'max timer 只在第一次 add 时创建')

        self.timers.pending_max_timers()[0].fire()
        self.assertEqual(len(self.flushed), 1)
        self.assertCountEqual(self.flushed[0], ['/tmp/file1.mp4', '/tmp/file2.mp4'])

        # 被 max timer 提前刷掉后, 残留的 calm timer 不会再产生第二批回调
        self.timers.last_pending_calm_timer().fire()
        self.assertEqual(len(self.flushed), 1)

        # _flush 把 _max_timer 置空, 下一次 add 会重新建一个
        self.buffer.add('/tmp/file3.mp4')
        self.assertEqual(len(self.timers.max_timers()), 2)

    def test_flush_empty_buffer_does_nothing(self):
        self.buffer._flush()
        self.assertEqual(self.flushed, [])

    def test_stop_cancels_timer(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.stop()
        self.assertEqual(self.timers.pending_calm_timers(), [])
        self.assertEqual(self.timers.pending_max_timers(), [])
        self.assertFalse(self.timers.calm_timers()[0].fire())
        self.assertFalse(self.timers.max_timers()[0].fire())
        self.assertEqual(self.flushed, [])

    def test_stale_flush_that_beat_cancel_flushes_once(self):
        self.buffer.add('/tmp/file1.mp4')
        stale = self.timers.last_pending_calm_timer()
        # 定时器线程已进入 _flush 并在 _lock 上排队, 而 add 持有 _lock
        stale.enter()
        self.buffer.add('/tmp/file2.mp4')

        # cancel() 落在已开始的回调上是空操作, 旧 timer 仍会把 {f1, f2} 刷出去
        self.assertFalse(stale.cancelled)
        stale.resume()
        self.assertEqual(len(self.flushed), 1)
        self.assertCountEqual(self.flushed[0], ['/tmp/file1.mp4', '/tmp/file2.mp4'])

        # 新 timer 随后开火时 buffer 已空, 不会再回调一次
        self.timers.last_pending_calm_timer().fire()
        self.assertEqual(len(self.flushed), 1)
