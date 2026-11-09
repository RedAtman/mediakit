import concurrent.futures
import logging
import subprocess
import time
from unittest import TestCase, main

# from config import CONFIG
from utils.executor import TaskManager

logger = logging.getLogger()


# @mock.patch.object(
#     CONFIG, "MEDIA_FILE_PATH", "./sample/input.mp4"
# )
class TestExecutor(TestCase):
    def test_subprocess_run(self):
        result = subprocess.run(
            ['ls'],
            input='-l',
            text=True,
            # capture_output=True,
            check=True,
        )
        logger.info(result)
        assert result.returncode == 0

    # def test_subprocess_run_list(self):
    #     result = subprocess.run(
    #         [
    #             "ffprobe",
    #             "-v",
    #             "error",
    #             "-select_streams",
    #             "v",
    #             "-show_streams",
    #             "-i",
    #             CONFIG.MEDIA_FILE_PATH,
    #             "|",
    #             "grep",
    #             "nb_frames",
    #             "|",
    #             "sed",
    #             "-e",
    #             "s/nb_frames=//",
    #         ],
    #         # input='-l',
    #         # text=True,
    #         # capture_output=True,
    #         check=True,
    #     )
    #     logger.info(result)
    #     assert result.returncode == 0

    # def test_subprocess_run_str(self):
    #     command = "ls -l"
    #     command = 'echo "foo"'
    #     command = f"ffprobe -v error -select_streams v -show_streams {CONFIG.MEDIA_FILE_PATH} | grep nb_frames | sed -e s/nb_frames=//"
    #     logger.info(command)
    #     result = subprocess.run(
    #         command,
    #         # 'ffprobe',
    #         # input='-l',
    #         text=True,
    #         # capture_output=True,
    #         check=True,
    #     )
    #     logger.info(result)
    #     assert result.returncode == 0

    # def test_subprocess_call_str(self):
    #     command = "ls -l"
    #     command = 'echo "foo"'
    #     command = str(
    #         f"ffprobe -v error -select_streams v -show_streams {CONFIG.MEDIA_FILE_PATH} | grep nb_frames | sed -e s/nb_frames=//"
    #     )
    #     result = subprocess.call(
    #         command,
    #         shell=True,
    #     )
    #     logger.info(result)
    #     assert result == 0

    # def test_subprocess_check_output(self):
    #     command = "ls -l"
    #     command = f"ffprobe -v error -select_streams v -show_streams {CONFIG.MEDIA_FILE_PATH} | \
    #         grep nb_frames | sed -e s/nb_frames=//"
    #     try:
    #         result = subprocess.check_output(
    #             command,
    #             shell=True,
    #         )
    #     except subprocess.CalledProcessError as err:
    #         logger.exception(err)
    #         raise err
    #     logger.info(result)
    #     self.assertIsInstance(result, bytes)


def task1():
    print('-->: task1')
    time.sleep(1)
    print('<--: task1')
    return 'task1'


def task2():
    print('-->: task2')
    time.sleep(2)
    print('<--: task2')
    return 'task2'


def task():
    print('-->: task')
    time.sleep(3)
    print('<--: task')
    return [task1, task2]


# def new_task():
#     print('new_task')
#     return 'new_task'

tasks = [task1, task2, task]


def callback(future):
    # time.sleep(1)
    print('-->: callback', id(future), future.result())


def callback2(future):
    print('-->: callback2', id(future), future.result())


class TestTaskManager(TestCase):
    def test_task_manager(self):
        task_manager = TaskManager()
        results = []

        with task_manager.executor:
            for _task in tasks:
                task_manager.submit(_task)
            logger.info('task_manager.futures: %s', task_manager.futures)
            self.assertEqual(len(task_manager.futures), 3)
            while task_manager.futures:
                for future in concurrent.futures.as_completed(task_manager.futures):
                    result = future.result()
                    logger.debug(result)
                    results.append(result)
                    task_manager.futures.remove(future)
        logger.info('Waiting for all subprocesses done...')
        self.assertEqual(len(results), 3)
        self.assertIn('task1', results)
        self.assertIn('task2', results)
        self.assertIsInstance(results[2], list)


if __name__ == '__main__':
    main(verbosity=2)


class TestTaskManagerResults(TestCase):
    def test_results_yield_in_completion_order_and_release_futures(self):
        """consuming results 必须逐步释放 Future, 否则整批在飞的引用都留着."""
        import time

        from utils.executor import TaskManager

        def job(delay):
            time.sleep(delay)
            return f'done-{delay}'

        manager = TaskManager(max_workers=2)
        manager.submit_all([lambda d=d: job(d) for d in (0.05, 0.01, 0.03)])

        collected = list(manager.results())

        self.assertEqual(sorted(collected), ['done-0.01', 'done-0.03', 'done-0.05'])
        # 最快的先出, 但断言顺序会引入 flaky; 断言释放即可
        self.assertEqual(manager.futures, [])
        self.assertEqual(manager.mapper_future_args, {})
