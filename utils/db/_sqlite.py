import logging
from queue import Queue
import sqlite3
import threading
from typing import Any, Dict, Optional, Tuple, Union

from config import CONFIG


logger = logging.getLogger()

__all__ = [
    "Engine",
]


class Engine:
    def __init__(self, database: str = CONFIG.SQLITE_DATABASE):
        self.database = database
        self.connection_pool: Queue[sqlite3.Connection] = Queue()
        self.lock = threading.Lock()
        self.create_connection_pool()
        logger.debug("Engine: %s", self)

    def create_connection_pool(
        self,
        pool_size: int = CONFIG.SQLITE_CONNECTION_POOL_SIZE,
    ):
        with self.lock:
            for _ in range(pool_size):
                connection = sqlite3.connect(
                    self.database,
                    # makes fetchall returns a datetime
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    check_same_thread=False,
                )
                self.connection_pool.put(connection)

    def get_connection(self) -> sqlite3.Connection:
        return self.connection_pool.get()

    def release_connection(self, connection: sqlite3.Connection) -> None:
        self.connection_pool.put(connection)

    def execute_query(
        self,
        query: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
    ):
        connection = self.get_connection()
        logger.debug("Connection: %s", connection)
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            connection.commit()
            return result
        finally:
            cursor.close()
            self.release_connection(connection)

    def execute_insert_update_delete(
        self,
        query: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
    ):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            self.release_connection(connection)

    def close_all_connections(self):
        with self.lock:
            while not self.connection_pool.empty():
                connection = self.connection_pool.get()
                connection.close()

    def get_cursor(self):
        return self.get_connection().cursor()

    def tables(self):
        return self.execute_query("SELECT name FROM sqlite_master WHERE type='table';")


def worker(db: Engine):
    result = db.execute_query("SELECT * FROM media")
    logger.debug(result)
    return result


if __name__ == "__main__":
    db = Engine(CONFIG.SQLITE_DATABASE)

    num_threads = 5
    # threads = []
    # for _ in range(num_threads):
    #     # thread = threading.Thread(target=worker, args=(db,))
    #     thread = threading.Thread(target=db.tables, args=())
    #     threads.append(thread)
    #     thread.start()

    # for thread in threads:
    #     thread.join()
    # logger.debug([thread.__dict__ for thread in threads])
    # db.close_all_connections()

    from utils.executor import TaskManager

    task_manager = TaskManager()
    with task_manager.executor:
        for _ in range(num_threads):
            task_manager.submit(db.tables)
    # logger.info([future.result() for future in task_manager.futures])
