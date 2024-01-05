from functools import cached_property

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

from logger import logger
from src import models
from utils.db.base import BaseEngine


class Engine(BaseEngine):
    def __init__(self, database: str):
        super().__init__(database)
        # e.g. sqlite:///sqlite.db | sqlite+aiosqlite:///sqlite.db | postgresql://user:password@localhost:5432/dbname
        self.database: str = f'sqlite:///{self.database}'
        self.metadata = models.Base.metadata

    def create_db_and_tables(self):
        self.conn = self.engine.connect()
        self.metadata.create_all(self.engine)

    def drop_tables(self):
        self.metadata.drop_all(self.engine)

    @cached_property
    def engine(self):
        return db.create_engine(
            self.database, echo=True,
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


if __name__ == '__main__':
    engine = Engine('sqlite.db')
    # engine.create_db_and_tables()
    with engine.get_session() as session:
        # result = session.execute(text('select * from media'))
        # result = session.execute(select(models.Media).where(models.Media.md5 == '3a51af5d5e4d3c8b84185729e91e0170').limit(1))
        params = {
            'md5': '3a51af5d5e4d3c8b84185729e91e0170',
        }
        # result = session.query(models.Media).filter_by(**params).all()
        # logger.debug(result)

        # result = models.Media.state['compress']
        # result = session.query(update(models.Media).values(data=models.Media.state + literal({"compress":3}, JSON)),)

        # result = session.query(models.Media).filter_by(**params).all()
        result = session.query(models.Media).filter_by(**params).update({'state': {'compress': 2}})
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
