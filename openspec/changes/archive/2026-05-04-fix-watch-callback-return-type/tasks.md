## 1. Fix _feed_existing to use middleware scheduler

- [ ] 1.1 Replace `Folder.run__('compress', medias=medias, max_workers=max_workers, callback_list=[_batch_callback])` in `_feed_existing` with `media_compress.core` scheduler via `functools.partial` + `Folder.run___()`
- [ ] 1.2 Add import: `from functools import partial` and `from .media import compress as media_compress` in watcher.py
- [ ] 1.3 Remove now-unused `Folder` import if no other callers remain in watcher.py (verify: `_feed_existing` is the only caller of `Folder(path)` — keep the `folder.scan_media()` / `folder.query()` part, only replace the `Folder.run__()` call)
- [ ] 1.4 Verify lint clean on watcher.py

## 2. Fix _flush_callback to use middleware scheduler

- [ ] 2.1 Replace `Folder.run__(action, medias=medias, max_workers=max_workers, callback_list=[_batch_callback])` in `_flush_callback` with the same `media_compress.core` + `Folder.run___()` pattern
- [ ] 2.2 Verify the `action` parameter can be removed (hardcode 'compress' since watcher only supports compress currently)
- [ ] 2.3 Verify lint clean on watcher.py

## 3. Test and verify

- [ ] 3.1 Run `pdm run lint` to verify no lint errors in changed files
- [ ] 3.2 Run full test suite: `pytest -vv` — all existing tests must pass
- [ ] 3.3 Run `mediakit compress -t video --watch -f /tmp/test_watch` with a test video file to verify: state updates to `{"compress": 2.0, "trim": -1.0}`, file moved to `.removed/`
- [ ] 3.4 Run `mediakit compress -t video --watch -f /tmp/test_watch_multi` with 3 test video files, verify sequential (not parallel) processing with max_workers=1

## 4. Deploy

- [ ] 4.1 Commit changes with descriptive message
- [ ] 4.2 Run `uv tool install --reinstall .` to deploy updated binary
- [ ] 4.3 Verify the uv tool binary works: `$HOME/.local/bin/mediakit compress -t video --watch -f /tmp/test_watch`
