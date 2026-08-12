import logging
from typing import Any, Generator

from sqlalchemy import Integer, TextClause, select
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.selectable import Select

from base.media import BaseMedia
from config import CONFIG
from src import models
from src.db import DatabaseEngine
from src.schemas import StateChoices
from utils.db import _sqlalchemy, base

logger = logging.getLogger()

__all__ = ['SqlAlchemyFolderMixin']


class BaseFolderMixin:
    path: str
    abspath: str
    engine: base.BaseEngine = DatabaseEngine.engine
    VALID_QUERY_TYPE = (Select, Update, str, TextClause)

    @classmethod
    def medias_(cls, path: str, media_type: str = 'video') -> Generator[BaseMedia, Any, None]: ...

    @staticmethod
    def query__(
        engine: base.BaseEngine, statement: Select | Update | str | TextClause, params: dict[str, Any] = {}
    ): ...

    # _DB_TABLE = 'media'
    _DB_MODEL: models.Base = models.Media
    _DB_TABLE = _DB_MODEL.__tablename__

    def get_query_statement(self, key: str) -> Select[tuple[models.Media]] | None:
        MAPPER_QUERY_STATEMENT = {
            'QUERY_UNPROCESSED': select(models.Media)
            .where(models.Media.dirname == self.abspath)
            .where(
                models.Media.state.op('->>')('compress')
                .cast(Integer)
                .in_([StateChoices.unprocessed, StateChoices.failed])
            )  # type: ignore
            # Failed (-2) is included so a transient failure (e.g. bad ffmpeg path at
            # startup) does not strand files forever; both states are retryable.
        }
        return MAPPER_QUERY_STATEMENT.get(key)

    @staticmethod
    def media__(path: str, media_type: str = 'video'):
        MEDIA_CLS: type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(media_type, BaseMedia)
        media = MEDIA_CLS(path)
        return media

    def query(self, statement: Select[Any] | Update | str | TextClause, params: dict[str, Any] = {}):
        return self.engine().query(statement, params)

    def scan_media(self, media_type: str = 'video'):
        medias = self.medias_(self.path, media_type)
        return self.scan_media_(self.path, medias, media_type)

    @classmethod
    def scan_media_(
        cls,
        path: str = CONFIG.MEDIA_FILE_FOLDER,
        medias: Generator[BaseMedia, None, None] | None = None,
        media_type: str = 'video',
    ):
        medias = cls.medias_(path, media_type)
        # try:
        #     result = cls.scan_media__(medias)
        #     return response.Result(code=200, data=result)
        # except Exception as err:
        #     logger.error(err)
        #     return response.Result(code=400, msg=err)
        return cls.scan_media__(medias)

    @classmethod
    def scan_media__(cls, medias: Generator[BaseMedia, None, None] | None = None):
        if medias is None:
            raise TypeError('medias is None.')
        return medias


class SqlAlchemyFolderMixin(BaseFolderMixin):
    _DB_ENGINE_CLS = _sqlalchemy.Engine
