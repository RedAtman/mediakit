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
                .notin_([StateChoices.finished, StateChoices.ignored])
            )  # type: ignore
            # 除了 finished(2) 和 ignored(-3), 其余都算可重试: 包括 failed(-2) 以及
            # 0.0-2.0 之间的进度值. 后者是任务被杀/崩溃时留下的中间态 —— 以前只认
            # -1/-2, 于是这些行永远不会再被取到 (库里曾积了 30 条, 全都指向已不在的文件).
            # cast(Integer) 会截断小数, 但我们只判"等不等于 2 / -3", 截断不影响结论.
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
        return self.scan_media_(self.path, media_type)

    @classmethod
    def scan_media_(cls, path: str = CONFIG.MEDIA_FILE_FOLDER, media_type: str = 'video'):
        # scan_media__ takes the generator, not the folder: it is the piece that also
        # serves the "medias came from somewhere else" case, so the path-only entry
        # point derives the stream here instead of accepting one it would drop.
        return cls.scan_media__(cls.medias_(path, media_type))

    @classmethod
    def scan_media__(cls, medias: Generator[BaseMedia, None, None] | None = None):
        if medias is None:
            raise TypeError('medias is None.')
        results = []
        for media in medias:
            try:
                # Explicit DB registration for discovered media (restores design
                # intent: scan folder file list → insert/update DB → query picks up
                # unprocessed rows). Uses media.md5 (cached property) for key.
                models.Media.get_or_create(md5=media.md5, title=media.title, dirname=media.dirname, ext=media.ext)
                results.append(media)
            except Exception as exc:
                logger.warning('Failed to register media %s in DB: %s', media.path, exc)
        return iter(results)


class SqlAlchemyFolderMixin(BaseFolderMixin):
    _DB_ENGINE_CLS = _sqlalchemy.Engine
