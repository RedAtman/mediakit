from datetime import datetime
from typing import Optional

from pydantic import validator
from sqlalchemy import Column
from sqlalchemy.orm import validates
from sqlmodel import JSON, Field, SQLModel

from config import CONFIG
from logger import logger
from src import schemas

__all__ = [
    'Media',
]


class Media(SQLModel, table=True):
    md5: str = Field(index=True, unique=True, primary_key=True)
    title: str = Field(nullable=False)
    dirname: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)
    state: schemas.State = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    # state: schemas.State = Field(Column(MutableDict.as_mutable(JSON)))

    __tablename__ = 'media'
    __table_args__ = (
        # UniqueConstraint('id', 'name', name='uix_id_name'),
        # Index('ix_id_name', 'name', 'email'),
    )

    # TODO: Needed for Column(JSON)?
    class Config:
        arbitrary_types_allowed = True

    # TODO: untested
    # def as_dict(self):
    #     return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def path(self):
        return f"{self.dirname}/{self.title}"

    @validates('state')
    def validate_state(cls, key: str, value: dict):
        logger.warning('-' * 80)
        # logger.info(('key', key, set(schemas.State.model_fields.keys())))
        logger.info(('value', type(value), value, set(value.keys())))
        invalid_keys = set(value.keys()) - set(schemas.State.model_fields.keys())
        if invalid_keys:
            raise TypeError(f"Field state does not allow keys: {invalid_keys}")
        return value

    # @validator('state')
    # def validate_state(cls, val: schemas.State, values: dict, **kwargs):
    #     # fields = Media.metadata.tables.get('media').columns.keys()
    #     # fields = schemas.State.model_fields.keys()
    #     # logger.debug(('values', values.keys()))
    #     # logger.debug(('kwargs', kwargs))
    #     logger.info(('val', type(val), val.dict()))
    #     fields = val.model_fields.keys()
    #     logger.info(('fields', fields))
    #     # logger.info(('val.model_fields.keys()', val.model_fields.keys()))
    #     for key in val.model_fields.keys():
    #         if key not in fields:
    #             raise ValueError(f"Field {key} is not allowed.")
    #             raise ValueError("Please ensure that the state provided has all the necessary fields.")
    #     return val


# Signal
from sqlalchemy import event


@event.listens_for(Media, 'before_update')
def on_media_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
    # logger.warning(('on_media_before_update', mapper, connection, target, ))


if __name__ == "__main__":
    from utils.db import _sqlmodel
    engine = _sqlmodel.Engine(CONFIG.SQLITE_DATABASE)
    engine.create_db_and_tables()
    company: Media = Media(
        md5='md5',
        title='title',
        dirname='dirname',
        # state={'compress': 'compress', 'trim': 'trim'},
        state = schemas.State(compress='compress', trim='trim')
    )
    logger.info(company)
    logger.info(company.model_dump())
    logger.info(company.model_dump_json())
    logger.info(company.state)
    # company = Company
