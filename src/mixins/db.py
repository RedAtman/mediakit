from datetime import datetime
import logging
from typing import Any, Dict, Generator, List, Optional, Type

from sqlalchemy import Integer, TextClause, select
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.selectable import Select

from base.media import BaseMedia
from config import CONFIG
from src import models
from src.db import DatabaseEngine
from src.schemas import StateChoices
from utils import response
from utils.db import _sqlalchemy, _sqlite, _sqlmodel, base


logger = logging.getLogger()

__all__ = [
    "SqlAlchemyFolderMixin",
    "SqlModelFolderMixin",
    "SqliteFolderMixin",
]


class BaseFolderMixin:
    path: str
    abspath: str
    engine: base.BaseEngine = DatabaseEngine.engine
    VALID_QUERY_TYPE = (Select, Update, str, TextClause)

    @classmethod
    def medias_(cls, path: str, media_type: str = "video") -> Generator[BaseMedia, Any, None]: ...

    @staticmethod
    def query__(
        engine: base.BaseEngine,
        statement: Select | Update | str | TextClause,
        params: dict[str, Any] = {},
    ): ...

    # _DB_TABLE = 'media'
    _DB_MODEL: models.Base = models.Media
    _DB_TABLE = _DB_MODEL.__tablename__

    def get_query_statement(self, key: str) -> Select[_sqlite.Tuple[models.Media]] | None:
        MAPPER_QUERY_STATEMENT = {
            "QUERY_UNPROCESSED": select(models.Media)
            .where(models.Media.dirname == self.abspath)
            .where(models.Media.state.op("->>")("compress").cast(Integer) == StateChoices.unprocessed),  # type: ignore
        }
        return MAPPER_QUERY_STATEMENT.get(key)

    @staticmethod
    def media__(path: str, media_type: str = "video"):
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(media_type, BaseMedia)
        media = MEDIA_CLS(path)
        return media

    def query(
        self,
        statement: Select[Any] | Update | str | TextClause,
        params: Dict[str, Any] = {},
    ):
        return self.engine.query(statement, params)

    def scan_media(
        self,
        media_type: str = "video",
    ):
        medias = self.medias_(self.path, media_type)
        return self.scan_media_(self.path, medias, media_type)

    @classmethod
    def scan_media_(
        cls,
        path: str = CONFIG.MEDIA_FILE_FOLDER,
        medias: Optional[Generator[BaseMedia, None, None]] = None,
        media_type: str = "video",
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
    def scan_media__(
        cls,
        medias: Optional[Generator[BaseMedia, None, None]] = None,
    ):
        if medias is None:
            raise TypeError("medias is None.")
        # TODO: Consider to discard this method.
        return list(medias)
        with cls.engine.get_session() as session:
            media_list: list[models.Base] = []
            for media in medias:
                _media = cls._DB_MODEL(
                    title=media.title + "." + media.ext,
                    md5=media.md5,
                    dirname=media.dirname,
                )
                session.add(_media)
                media_list.append(_media)
            try:
                _ = session.commit()
                return response.Result(code=0, data=media_list)
            except Exception as err:
                logger.error(err.__dict__)
                session.rollback()
                return response.Result(code=1, msg=err)


class SqlAlchemyFolderMixin(BaseFolderMixin):
    _DB_ENGINE_CLS = _sqlalchemy.Engine


class SqlModelFolderMixin(BaseFolderMixin):
    _DB_ENGINE_CLS = _sqlmodel.Engine


# TODO: maybe need refactor.
class SqliteFolderMixin(BaseFolderMixin):
    _DB_ENGINE_CLS = _sqlite.Engine

    @classmethod
    def scan_media__(
        cls,
        medias: Optional[Generator[BaseMedia, None, None]] = None,
    ):
        if medias is None:
            logger.warning("medias is None.")
            raise TypeError
        cls.engine.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS {cls._DB_TABLE} (
                # id INT PRIMARY KEY default(random()),
                title TEXT UNIQUE,
                md5 TEXT NOT NULL UNIQUE,
                dirname TEXT,
                created_date TIMESTAMP,
                state JSON,
            )
        """
        )
        result_list: List[Any] = []
        for media in medias:
            result = cls.engine.execute_insert_update_delete(
                f"INSERT OR IGNORE INTO {cls._DB_TABLE} (title, md5, dirname, created_date) VALUES (?, ?, ?, ?)",
                (
                    media.title + "." + media.ext,
                    media.md5,
                    media.dirname,
                    datetime.now(),
                ),
            )
            result_list.append(result)
        return result_list

    # TODO: remove all update_state method.
    @classmethod
    def update_state_(cls, media: BaseMedia, key: str, value: Any):
        result = cls.engine.execute_query(f"SELECT * FROM {cls._DB_TABLE} WHERE md5 = ?", (media.md5,))
        logger.info(
            (
                "result",
                type(result),
                result,
                result[0][0],
                media.title + "." + media.ext,
                media.md5,
            )
        )
        return cls.engine.execute_query(
            f"UPDATE {cls._DB_TABLE} SET state = json_set(state, '$.{key}', ?) WHERE md5 = ?",
            (value, media.md5),
        )

    def query_state(self, path, media_type: str = "video"):
        """Query media state."""
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(media_type, BaseMedia)
        media = MEDIA_CLS(path)
        return self._query_state(media)

    @classmethod
    def _query_state(cls, media: BaseMedia):
        result = cls.engine.execute_query(f"SELECT * FROM {cls._DB_TABLE} WHERE md5 = ?", (media.md5,))
        logger.info(
            (
                "result",
                type(result),
                result,
                result[0][0],
                media.title + "." + media.ext,
                media.md5,
            )
        )
        return cls.engine.execute_query(
            f"SELECT title, json(state) FROM {cls._DB_TABLE} WHERE md5 = ?",
            (media.md5,),
        )
