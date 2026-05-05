## 1. State Tracking Infrastructure

- [x] 1.1 Add instance attributes to `WatcherScheduler.__init__`: `_config_filepath`, `_config_mtime`, `_config_poll_interval`, `_last_config_check`, `_watched_paths` (set), `_path_to_watch` (dict), `_handler` reference, and watcher parameter cache (`_recursive`, `_media_type`, `_max_workers`, `_action`)
- [x] 1.2 Modify `_setup_observer` to store `self._handler` after creating the `_WatchEventHandler` instance
- [x] 1.3 Modify `_setup_multi_observer` to store `self._handler` after creating the `_WatchEventHandler` instance
- [x] 1.4 After observer setup in `core()`, save resolved config file path, populate `_watched_paths` from `valid_paths`, and cache watcher parameters as instance attributes
- [x] 1.5 After observer setup in `core()`, save `self._config_mtime` from `os.path.getmtime()` if config file exists

## 2. Config Change Detection

- [x] 2.1 Implement `_check_config_file_changes()` method: poll mtime, detect changes, compute path diff
- [x] 2.2 Implement the diff logic: `to_add = new_valid - old` and `to_remove = old - new_valid`
- [x] 2.3 Implement `to_remove` handling: `observer.unschedule(watch)` for each removed path, update tracking state
- [x] 2.4 Implement `to_add` handling: `observer.schedule(self._handler, path, recursive=recursive)` for each new path, update tracking state
- [x] 2.5 On `to_add`, call `_feed_existing()` for each new path to catch pre-existing media files
- [x] 2.6 Add `INFO`-level logging for all add/remove/skip actions during config sync

## 3. Event Loop Integration

- [x] 3.1 Modify `_run_event_loop()` to call `_check_config_file_changes()` on each iteration (rate-limited by `_config_poll_interval`)
- [x] 3.2 Wire `_check_config_file_changes` into the `_stop_event` loop guard so it stops when shutdown is signaled

## 4. Error Handling

- [x] 4.1 Wrap `_parse_folder_file()` call in `_check_config_file_changes()` with try/except — on failure, log warning and preserve current watches
- [x] 4.2 Handle missing config file: `os.path.isfile()` check before reading; if missing, log info and skip; if re-appears, resume monitoring
- [x] 4.3 Validate new directories with `os.path.isdir()` before scheduling (same as existing startup behavior)

## 5. Testing

- [x] 5.1 Test: config file modified with new directory — verify `observer.schedule()` called, `_feed_existing()` called, log message emitted
- [x] 5.2 Test: config file modified with directory removed — verify `observer.unschedule()` called, path removed from tracking state
- [x] 5.3 Test: config file modified with both add and remove — verify both operations in a single poll cycle
- [x] 5.4 Test: config file mtime unchanged — verify no observer operations
- [x] 5.5 Test: config file deleted at runtime — verify current watches maintained, no crash
- [x] 5.6 Test: config file with invalid content — verify warning logged, current watches maintained
- [x] 5.7 Test: new path in config is not a valid directory — verify skipped with warning
