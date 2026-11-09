from contextlib import contextmanager
from datetime import datetime
import logging
from typing import Generator, Union, Unpack

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, declarative_base

from src import db, schemas
from src.models._type import MediaParams
from utils import response

logger = logging.getLogger()

__all__ = ['Base', 'Media']

Base = declarative_base()


@contextmanager
def _session() -> Generator[Session, None, None]:
    """The engine's session with this model's metadata attached.

    Engine 现在不 import 具体模型, 所以元数据由模型侧补齐; 放在这里是因为
    Media 的四个读写方法都需要, 重复四遍只会漂移.
    """
    engine = db.DatabaseEngine.engine()
    if engine.metadata is None:
        engine.metadata = Base.metadata
    with engine.get_session() as session:
        yield session


class Media(Base):
    md5 = Column(String, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    ext = Column(String, nullable=False, default='')
    dirname = Column(String, nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow, read_only=True)
    _created_at = Column('created_at', DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=None, nullable=True)
    state = Column(JSON, default=schemas.State().model_dump(), nullable=False)

    @hybrid_property
    def created_at(self):
        """Make created_at read-only"""
        return self._created_at

    __tablename__ = 'media'

    __table_args__ = (
        # UniqueConstraint('id', 'name', name='uix_id_name'),
        # Index('ix_id_name', 'name', 'email'),
    )

    def __str__(self) -> str:
        return f'<{self.__class__.__name__}({self.__dict__})>'

    # def model_dump_json(self):
    #     return schemas.Media(**self.model_dump()).json()

    @property
    def path(self):
        if self.ext:
            return f'{self.dirname}/{self.title}.{self.ext}'
        return f'{self.dirname}/{self.title}'

    @classmethod
    def get(cls, **kwargs: Unpack[MediaParams]):
        with _session() as session:
            instance = session.query(cls).filter_by(**kwargs).first()
            return instance

    @classmethod
    def get_or_create(cls, **kwargs: Unpack[MediaParams]):
        md5 = kwargs.get('md5')
        if not md5:
            raise ValueError('md5 is required for get_or_create')
        with _session() as session:
            instance = session.query(cls).filter_by(md5=md5).first()
            if instance:
                if instance.state.get('compress') == schemas.StateChoices.finished:
                    return instance
                changed = False
                for key in ('title', 'dirname', 'ext'):
                    if key in kwargs and getattr(instance, key) != kwargs[key]:
                        setattr(instance, key, kwargs[key])
                        changed = True
                if changed:
                    instance.updated_at = datetime.utcnow()
                    session.add(instance)
                    session.commit()
            else:
                instance = cls(**kwargs)
                session.add(instance)
                try:
                    session.commit()
                except Exception as exc:
                    logger.error(f'{exc}, MD5: {md5}')
                    session.rollback()
            return instance

    def update_state(self, key: str, val: Union[int, float]):
        logger.debug(
            'update_state: key=%s, val=%s (type=%s), current self.state=%s', key, val, type(val).__name__, self.state
        )
        with _session() as session:
            state: dict = self.state.copy()  # type: ignore
            state[key] = val
            new_state = schemas.State(**state).model_dump()
            logger.debug('update_state: new_state=%s, before session.add', new_state)
            self.state = new_state
            session.add(self)
            session.commit()
            logger.debug('update_state: committed, md5=%s, state=%s', self.md5, self.state)
            return response.Result(code=0, data={'media': self})

    def delete(self):
        with _session() as session:
            session.delete(self)
            session.commit()
            return response.Result(code=0, data={'media': self})
