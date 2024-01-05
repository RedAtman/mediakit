from contextlib import contextmanager
from typing import Generator, Type

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm import Session

from logger import logger


class BaseEngine:

    engine: Engine
    metadata: MetaData
    conn: Connection
    session: Type[Session]

    def __init__(self, database: str):
        self.database: str = database

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.session()
        if not isinstance(session, Session):
            raise TypeError(f'Expected Session, got {type(session)}')
        try:
            yield session
        except Exception as err:
            session.rollback()
            logger.error(err)
            # return response.Result(code=400, msg=err)
            raise err
        finally:
            session.close()
