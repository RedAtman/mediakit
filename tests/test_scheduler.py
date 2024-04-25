from dataclasses import dataclass
import logging
import unittest

from src.schedulers import folder


logger = logging.getLogger()


@dataclass
class kwargs:
    folder: str = "samples"
    type: str = "video"
    worker: int = 1
    daemon: bool = True
    action: str = "compress"


logger.info(kwargs.action)


class TestScheduler(unittest.TestCase):

    def test_cli(self):
        scheduler = getattr(folder, kwargs.action)
        # logger.debug(scheduler)
        result = getattr(scheduler, "core")(**kwargs.__dict__)
        logger.info(result)
        assert isinstance(result, list)


if __name__ == "__main__":
    unittest.main()
