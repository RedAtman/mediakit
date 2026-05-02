import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestContextEnforcement(unittest.TestCase):
    """Tests for ctx.next() enforcement in MiddlewareScheduler._wrap()."""

    def setUp(self):
        import importlib
        import src.patterns.middleware_context_closure as mc
        importlib.reload(mc)
        self.mc = mc

    def test_missing_ctx_next_raises(self):
        """Middleware that returns without calling ctx.next() should raise RuntimeError."""
        def bad_middleware(ctx, **kwargs):
            return {'result': 'early'}

        def core(**kwargs):
            return {'core': 'ran'}

        scheduler = self.mc.MiddlewareScheduler()
        scheduler.add_middleware(bad_middleware)
        scheduler.add_func('test')(core)
        scheduler.initialize()

        wrapped = getattr(scheduler, 'test')
        with self.assertRaises(RuntimeError) as exc:
            wrapped(**{})
        self.assertIn('ctx.next()', str(exc.exception))

    def test_normal_chain_succeeds(self):
        """Normal chain where middleware calls ctx.next() succeeds."""
        def good_middleware(ctx, **kwargs):
            return ctx.next(**kwargs)

        def core(**kwargs):
            return {'core': 'ran'}

        scheduler = self.mc.MiddlewareScheduler()
        scheduler.add_middleware(good_middleware)
        scheduler.add_func('test')(core)
        scheduler.initialize()

        wrapped = getattr(scheduler, 'test')
        result = wrapped(**{})
        self.assertEqual(result, {'core': 'ran'})


class TestLoadMiddleware(unittest.TestCase):
    """Tests for _load_middleware path resolution."""

    def setUp(self):
        import importlib
        import src.patterns.middleware_context_closure as mc
        importlib.reload(mc)
        self.mc = mc

    def test_load_middleware_with_chain(self):
        """_load_middleware returns a callable that invokes middlewares in order."""
        calls = []

        def mw1(ctx, **kwargs):
            calls.append('mw1')
            return ctx.next(**kwargs)

        def mw2(ctx, **kwargs):
            calls.append('mw2')
            return ctx.next(**kwargs)

        def core(**kwargs):
            calls.append('core')
            return 'done'

        scheduler = self.mc.MiddlewareScheduler()
        scheduler.add_middleware(mw1)
        scheduler.add_middleware(mw2)
        scheduler.add_func('test')(core)
        scheduler.initialize()

        result = getattr(scheduler, 'test')(**{})
        self.assertEqual(result, 'done')
        self.assertEqual(calls, ['mw1', 'mw2', 'core'])

    def test_empty_middleware_chain(self):
        """No middlewares — core runs directly."""
        def core(**kwargs):
            return 'direct'

        scheduler = self.mc.MiddlewareScheduler()
        scheduler.add_func('test')(core)
        scheduler.initialize()

        result = getattr(scheduler, 'test')(**{})
        self.assertEqual(result, 'direct')

    def test_load_middleware_returns_list(self):
        """_load_middleware returns a callable (not a list)."""
        scheduler = self.mc.MiddlewareScheduler()
        ctx = self.mc.Context()
        result = scheduler._load_middleware(ctx, lambda **kw: 'ok')
        self.assertTrue(callable(result))
