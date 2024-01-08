from contextlib import contextmanager
from typing import Any, AsyncGenerator, Iterator

from sqlalchemy import select, text
import sqlalchemy.exc
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
import sqlalchemy.orm.exc
from sqlmodel import Session, SQLModel, create_engine, select

from logger import logger
from utils import response

from .base import BaseEngine

__all__ = [
    'Engine',
]


class Engine(BaseEngine):
    def __init__(self, database: str):
        super().__init__(database)
        # e.g. sqlite:///sqlite.db | sqlite+aiosqlite:///sqlite.db | postgresql://user:password@localhost:5432/dbname
        self.database: str = f'sqlite:///{self.database}'
        self.engine = create_engine(
            self.database, echo=True,
            # connect_args={'check_same_thread': False},
            max_overflow=0,  # 超过连接池大小外最多创建的连接
            pool_size=5,  # 连接池大小
            pool_timeout=30,  # 池中没有线程最多等待的时间 否则报错
            pool_recycle=-1  # 多久之后对线程池中的线程进行一次连接的回收（重置）
        )

    def create_db_and_tables(self):
        return SQLModel.metadata.create_all(self.engine, checkfirst=True)

    def drop_tables(self):
        SQLModel.metadata.drop_all(self.engine, checkfirst=True)

    @property
    def SessionLocal(self):
        session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )
        # Use scoped_session to create a thread-local session. For thread safety, it’s usually best to create a new Session instance for each incoming request, and scope it to that request.
        return scoped_session(session_factory)
        return sessionmaker(bind=engine, autocommit=False, autoflush=False)

    @property
    def AsyncSessionLocal(self):
        async_engine: AsyncEngine = create_async_engine(self.database)
        return async_sessionmaker(
            bind=async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    # @property
    # def session(self) -> Session:
    #     return self.get_session()

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        session = self.SessionLocal()
        try:
            yield session
        # except Exception as err:
        #     session.rollback()
        #     logger.error(err)
        #     raise err
        finally:
            session.close()

    # TODO: Unverified
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.AsyncSessionLocal() as session:
            yield session

    def query__(self, query: str, params: dict[str, Any]={}):
        # statement = select(models.Media).where(
        #     models.Media.dirname == self.abspath,
        #     # cast(models.Media.state['trim'], String) == 2,
        #     text("state->>'trim' IS NULL")
        # )
        stmt = sqlalchemy.text(query)
        with self.get_session() as session:
            try:
                # session.exec(stmt, params)
                medias = session.execute(stmt, params)
                # medias = session.execute(statement).all()
            except sqlalchemy.exc.NoResultFound as err:
                logger.error(err)
                return response.Result(code=400, msg=err)
            except Exception as err:
                logger.error(err)
                return response.Result(code=400, msg=err)
            return response.Result(code=200, data=medias)


if __name__ == "__main__":
    engine = Engine("sqlite:///sqlite.db")
    from models.media import Media

    # synchronous usage
    with engine.get_session() as session:
        # use session here
        result = session.execute(text("SELECT * FROM media"))
        print(result.all())
        statement = select(Media)
        result = session.execute(statement)
        print(result.all())

    # # asynchronous usage
    # async with engine.get_async_session() as session:
    #     # use session here
    #     pass
