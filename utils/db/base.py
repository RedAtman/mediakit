import abc
from contextlib import contextmanager
from typing import Any, Generator, Type

from sqlalchemy import MetaData, TextClause
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.selectable import Select

from logger import logger


class BaseEngine(abc.ABC):

    engine: Engine
    metadata: MetaData
    conn: Connection
    session: Type[Session]

    @abc.abstractmethod
    def query__(self, statement: Select|Update|str|TextClause, params: dict[str, Any]={}):
        pass

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

    def query(self, statement: Select|Update|str|TextClause, params: dict[str, Any]={}):
        return self.query__(statement, params)
