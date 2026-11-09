"""utils/ 是底层库, src/ && base/ 才允许依赖它 — 反向依赖会让底层库无法独立测试."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _imports_of(package: str) -> list[tuple[str, int, str]]:
    hits = []
    for path in (ROOT / package).rglob('*.py'):
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if re.match(r'\s*(from|import)\s+(src|base)\b', line):
                hits.append((str(path.relative_to(ROOT)), lineno, line.strip()))
    return hits


class TestImportSideEffects(unittest.TestCase):
    def test_importing_schedulers_does_not_start_the_throttler(self):
        """import 不该起后台线程: coordinator 必须等到真正跑任务时才创建."""
        import importlib
        import sys

        for name in [m for m in sys.modules if m.startswith('src.schedulers')]:
            del sys.modules[name]
        module = importlib.import_module('src.schedulers.folder')

        self.assertIsNone(module._coordinator, 'import 阶段不该创建 CPU 节流协调器')


class TestLayering(unittest.TestCase):
    def test_utils_does_not_import_src_or_base(self):
        self.assertEqual(_imports_of('utils'), [], 'utils/ 不能反向依赖 src/ 或 base/')

    def test_src_file_does_not_import_schedulers(self):
        offenders = [
            (str(p.relative_to(ROOT)), n, line.strip())
            for p in (ROOT / 'src' / 'file').rglob('*.py')
            for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1)
            if re.match(r'\s*(from|import)\s+src\.schedulers\b', line)
        ]
        self.assertEqual(offenders, [], 'src/file/ 是通用工具, 不应依赖调度器')


class TestStartupImports(unittest.TestCase):
    """启动链不该带上看库/翻译/进度条才需要的重依赖 (实测各值数 MB)."""

    def _imported_after(self, code):
        import json
        import subprocess
        import sys

        out = subprocess.run(
            [sys.executable, '-c', f'import sys, json; {code}; print(json.dumps(sorted(sys.modules)))'],
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        return set(json.loads(out.stdout))

    def test_requests_is_not_loaded_by_the_watcher(self):
        loaded = self._imported_after('import src.schedulers.watcher')
        self.assertNotIn('requests', loaded, 'utils.translator 只有 save_metadata 需要, 必须延迟导入')

    def test_tqdm_is_not_loaded_by_the_watcher(self):
        loaded = self._imported_after('import src.schedulers.watcher')
        self.assertNotIn('tqdm', loaded, 'tqdm 只有开始处理媒体时才需要, 必须延迟导入')
