from functools import cached_property
import logging
from typing import Any

import sqlalchemy as db
from sqlalchemy import TextClause, text
import sqlalchemy.exc
from sqlalchemy.orm import sessionmaker
import sqlalchemy.orm.exc
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.selectable import Select

from src import models
from utils import response
from utils.db.base import BaseEngine


logger = logging.getLogger()


class Engine(BaseEngine):
    def __init__(self, database: str):
        super().__init__(database)
        # e.g. sqlite:///sqlite.db | sqlite+aiosqlite:///sqlite.db | postgresql://user:password@localhost:5432/dbname
        self.database: str = f"sqlite:///{self.database}"
        self.metadata = models.Base.metadata

    def create_db_and_tables(self):
        self.conn = self.engine.connect()
        self.metadata.create_all(self.engine)

    def drop_tables(self):
        self.metadata.drop_all(self.engine)

    @cached_property
    def engine(self):
        return db.create_engine(
            self.database,
            echo=True,
            isolation_level="READ UNCOMMITTED",
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

    def query__(
        self, statement: Select | Update | str | TextClause, params: dict[str, Any] = {}
    ):
        if isinstance(statement, str):
            statement = text(statement)
        with self.get_session() as session:
            try:
                # session.exec(statement, params)
                if isinstance(statement, Select):
                    result = session.execute(statement, params).scalars().all()
                elif isinstance(statement, Update):
                    # result = session.query(models.Media).filter(models.Media.md5 == '3a51af5d5e4d3c8b84185729e91e0170').update(
                    #     {'state': func.json_set(models.Media.state, "$.compress", 0)},
                    #     synchronize_session='fetch'
                    # )
                    _result = session.execute(statement, params)
                    result = _result.__dict__
                    if result.get("rowcount") is 0:
                        return response.Result(code=404)
                elif isinstance(statement, TextClause):
                    result = session.execute(statement, params)
                else:
                    result = {}
                session.commit()
            except sqlalchemy.exc.NoResultFound as err:
                logger.error(err)
                return response.Result(code=400, msg=err)
            except Exception as err:
                logger.error(err)
                return response.Result(code=400, msg=err)
            return response.Result(code=0, data=result)


if __name__ == "__main__":
    engine = Engine("sqlite.db")
    # engine.create_db_and_tables()
    with engine.get_session() as session:
        # result = session.execute(text('select * from media'))
        # result = session.execute(select(models.Media).where(models.Media.md5 == '3a51af5d5e4d3c8b84185729e91e0170').limit(1))
        params = {
            "md5": "3a51af5d5e4d3c8b84185729e91e0170",
        }
        # result = session.query(models.Media).filter_by(**params).all()
        # logger.debug(result)

        # result = models.Media.state['compress']
        # result = session.query(update(models.Media).values(data=models.Media.state + literal({"compress":3}, JSON)),)

        # result = session.query(models.Media).filter_by(**params).all()
        result = (
            session.query(models.Media)
            .filter_by(**params)
            .update({"state": {"compress": 2}})
        )
        logger.debug(result)
        # {'_orig': (275265937, 275609729), '_propagate_attrs': immutabledict({'compile_state_plugin': 'orm', 'plugin_subject': <Mapper at 0x1067e8890; Media>}), 'left': Column('state', JSON(), table=<media>), 'right': BindParameter('%(4409755664 state)s', 'compress', type_=JSONStrIndexType()), 'operator': <function json_getitem_op at 0x1037ad800>, 'type': JSON(), 'negate': None, '_is_implicitly_boolean': False, 'modifiers': {}}
        session.commit()

        # Map the result to the model
        # for row in result.fetchall():
        #     logger.debug((type(row), row._mapping, type(row._mapping.get('state')), type(row._asdict().get('state')), ))
        #     logger.json(models.Media(**row._mapping))
        #
        # media_list = [models.Media(row.__dict__) for row in result.fetchall()]
        # logger.json(media_list)
