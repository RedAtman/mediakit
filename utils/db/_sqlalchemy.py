from functools import cached_property
import logging
from typing import Any, Dict

import sqlalchemy as db
from sqlalchemy import MetaData, TextClause, text
import sqlalchemy.exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.selectable import Select

from utils.db.base import BaseEngine

logger = logging.getLogger()


class Engine(BaseEngine):
    def __init__(self, database: str, metadata: MetaData | None = None):
        super().__init__(database, metadata)
        # e.g. sqlite:///sqlite.db | sqlite+aiosqlite:///sqlite.db | postgresql://user:password@localhost:5432/dbname
        self.database: str = f'sqlite:///{self.database}'

    def create_db_and_tables(self):
        if self.metadata is None:
            raise ValueError('create_db_and_tables() needs metadata; pass it to the constructor')
        self.conn = self.engine.connect()
        self.metadata.create_all(self.engine)

    def drop_tables(self):
        if self.metadata is None:
            raise ValueError('drop_tables() needs metadata; pass it to the constructor')
        self.metadata.drop_all(self.engine)

    @cached_property
    def engine(self):
        return db.create_engine(
            self.database,
            # creates StreamHandler which outputs to console.
            # echo=True,
            isolation_level='READ UNCOMMITTED',
            # json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
        )

    @cached_property
    def session(self):
        return sessionmaker(
            self.engine,
            # bind=self.engine,
            expire_on_commit=False,
            # autocommit=False,
            # autoflush=False,
        )

    def query__(self, statement: Select | Update | str | TextClause, params: Dict[str, Any] = {}):
        from utils import response

        if isinstance(statement, str):
            statement = text(statement)
        with self.get_session() as session:
            try:
                # session.exec(statement, params)
                if isinstance(statement, Select):
                    result = session.execute(statement, params).scalars().all()
                elif isinstance(statement, Update):
                    _result = session.execute(statement, params)
                    # CursorResult.rowcount 是惰性属性, 不看属性只看 __dict__ 永远拿到 None,
                    # 导致所有 UPDATE 都误判为 0 行命中 (而 404 也不是合法的 ResultStatus)
                    rowcount = getattr(_result, 'rowcount', None)
                    if rowcount == 0:
                        return response.Result(code=response.ResultStatus.FAILED, msg=f'No rows matched: {statement}')
                    # 不把 CursorResult 内部结构当 data 泄出去, 只回报命中行数
                    result = {'rowcount': rowcount}
                elif isinstance(statement, TextClause):
                    result = session.execute(statement, params)
                else:
                    result = {}
                session.commit()
            except sqlalchemy.exc.NoResultFound as err:
                logger.exception(err)
                return response.Result(code=600, msg=err)
            except Exception as err:
                logger.exception(err)
                return response.Result(code=600, msg=err)
            return response.Result(code=0, data=result)
