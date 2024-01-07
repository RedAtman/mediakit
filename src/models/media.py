from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

from config import CONFIG
from logger import logger
from src import db, schemas

__all__ = [
    'Base',
    'Media',
]

Base = declarative_base()

class Media(Base):
    md5 = Column(String, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    dirname = Column(String, nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow, read_only=True)
    _created_at = Column('created_at', DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=None, nullable=True)
    state = Column(JSON, default=schemas.State().model_dump(), nullable=False)

    @hybrid_property
    def created_at(self):
        '''Make created_at read-only'''
        return self._created_at

    # @created_at.setter
    # def created_at(self, value):
    #     self._created_at = value

    __tablename__ = 'media'
    # @classmethod
    # def __tablename__(cls):
    #     return 'media'

    __table_args__ = (
        # UniqueConstraint('id', 'name', name='uix_id_name'),
        # Index('ix_id_name', 'name', 'email'),
    )

    # def __repr__(self):
    #     return f"<Media(md5={self.md5}, title={self.title}, dirname={self.dirname}, created_at={self.created_at}, updated_at={self.updated_at}, state={self.state})>"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"


    # def model_dump(self):
    #     return {
    #         'md5': self.md5,
    #         'title': self.title,
    #         'dirname': self.dirname,
    #         'created_at': self.created_at,
    #         'updated_at': self.updated_at,
    #         'state': self.state,
    #     }

    # def model_dump_json(self):
    #     return schemas.Media(**self.model_dump()).json()

    # TODO: untested
    # def as_dict(self):
    #     return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def path(self):
        return f"{self.dirname}/{self.title}"

    # @hybrid_property
    # def compress(self) -> Any:
    #     return self.state.get('compress')

    # @compress.setter
    # def compress(self, value):
    #     self.state['compress'] = value

    # @compress.expression
    # def compress(cls):
    #     return func.json_extract(cls.state, '$.compress')

    # @compress.update_expression
    # def compress(cls, value):
    #     return [
    #         (cls.state, func.json_set(cls.state, '$.compress', value))
    #     ]

    # @validates('state')
    # def validate_state(cls, key: str, state: dict):
    #     # logger.info(('key', key, state, set(schemas.State.model_fields.keys())))
    #     # invalid_keys = set(state.keys()) - set(schemas.State.model_fields.keys())
    #     # if invalid_keys:
    #     #     raise TypeError(f"Field state does not allow keys: {invalid_keys}")
    #     logger.debug(('validate_state', key, state, type(state), schemas.State(**state).model_dump()))
    #     state = schemas.State(**state).model_dump()
    #     return state

    @classmethod
    def get(cls, **kwargs: dict[str, Any]):
        with db.DatabaseEngine.engine.get_session() as session:
            instance = session.query(cls).filter_by(**kwargs).first()
            return instance

    @classmethod
    def get_or_create(cls, **kwargs: dict[str, str]):
        with db.DatabaseEngine.engine.get_session() as session:
            instance = session.query(cls).filter_by(**kwargs).first()
            if not instance:
                instance = cls(**kwargs)
                session.add(instance)
                session.commit()
                return instance
            return instance

    def update_state(self, key: str, val: int):
        with db.DatabaseEngine.engine.get_session() as session:
            state: dict = self.state.copy() # type: ignore
            # state = dict(self.state)
            state[key] = val
            self.state = schemas.State(**state).model_dump()
            session.add(self)
            session.commit()
            return self


# Signal
from sqlalchemy import event


@event.listens_for(Media, 'before_update')
def on_media_before_update(mapper, connection, target):
    # target.state = schemas.State(**target.state).model_dump()
    target.updated_at = datetime.utcnow()
    logger.warning(('on_media_before_update', mapper, connection, target, ))


if __name__ == "__main__":
    from utils.db import _sqlmodel
    engine = _sqlmodel.Engine(CONFIG.SQLITE_DATABASE)
    # engine.create_db_and_tables()
    company: Media = Media(
        md5='md5',
        title='title',
        dirname='dirname',
        # state={'compress': 'compress', 'trim': 'trim'},
        state = schemas.State(
            compress=schemas.StateChoices.undo,
            trim=schemas.StateChoices.undo,
        )
    )
    logger.json(company)
    logger.json(company.__dict__)
    logger.json(company.state)
