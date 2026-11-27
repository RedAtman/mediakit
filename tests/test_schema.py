import logging
import unittest

from pydantic import ValidationError

from src import schemas

logger = logging.getLogger()


class SchemaTest(unittest.TestCase):
    def test_accepts_enum_and_number(self):
        state = schemas.State(compress=schemas.StateChoices.finished, trim=2)
        assert isinstance(state, schemas.State)
        assert state.compress == schemas.StateChoices.finished
        assert state.trim == 2

    def test_untouched_actions_leave_no_keys(self):
        """没执行过的 action 不该在 state 里留 key: 以前每行都带 compress/trim 两个 -1."""
        state = schemas.State()
        assert state.compress is None
        assert state.trim is None
        assert state.dump() == {}

    def test_dump_keeps_only_written_keys(self):
        assert schemas.State(compress=schemas.StateChoices.finished).dump() == {'compress': 2}
        # trim 目前没有任何 scheduler 会写它, 所以它不应该凭空出现
        assert 'trim' not in schemas.State(compress=-1).dump()

    def test_existing_keys_survive_a_round_trip(self):
        """旧行里已有的 key 会一直保留: dump() 只丢 "没提供" 的 key.

        所以把库从 "compress+trim" 迁到 "按需" 必须做一次数据迁移, 光改代码不够.
        """
        legacy = {'compress': 2.0, 'trim': -1.0}
        assert schemas.State(**legacy).dump() == legacy

    def test_rejects_out_of_range(self):
        # -3 ignored / -2 failed / -1 unprocessed / 0.0-1.0 in progress / 2 finished
        for bad in (3, -4):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                schemas.State(compress=bad)

    def test_accepts_ignored(self):
        # ffprobe 打不开的产物是终态 ignored, 不是 failed: 不能再被重试
        state = schemas.State(compress=schemas.StateChoices.ignored)
        assert state.compress == -3
        assert schemas.StateChoices.ignored < schemas.StateChoices.failed
