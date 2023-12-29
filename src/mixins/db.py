from datetime import datetime
import functools
from typing import Any, Generator, List, Optional, Type

import sqlalchemy.exc
import sqlalchemy.orm.exc
from sqlmodel import select

from base import BaseMedia
from config import CONFIG
from logger import logger
from src import models, schemas
from utils.db import _sqlite, _sqlmodel

__all__ = [
    'SqliteFolderMixin',
]

class BaseFolderMixin:
    path: str

    @classmethod
    def _medias(cls, path: str, media_type: str='video') -> Generator[BaseMedia, Any, None]:
        ...

    @classmethod
    def scan_media__(cls, medias: Optional[Generator[BaseMedia, Any, None]]=None):
        ...

    @classmethod
    def update_state_(cls, path: str, key: str, value: Any):
        ...

    _DB_TABLE = 'media'
    _ENGINE_CLS = _sqlmodel.Engine

    @classmethod
    @property
    @functools.cache
    def engine(cls) -> _ENGINE_CLS:
        return cls._ENGINE_CLS(CONFIG.SQLITE_DATABASE)

    @staticmethod
    def media__(path: str, media_type: str='video'):
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(media_type, BaseMedia)
        media = MEDIA_CLS(path)
        logger.info(('media', media, media.title, media.ext, media.md5))
        return media

    def scan_media(self):
        return self.scan_media_(self.path)

    @classmethod
    def scan_media_(
        cls, path: str=CONFIG.MEDIA_FILE_FOLDER,
        media_type: str='video',
    ):
        medias = cls._medias(path, media_type)
        try:
            return cls.scan_media__(medias)
        except sqlalchemy.exc.IntegrityError as err:
            return [{
                'msg': err.orig,
                'params': err.params,
            }]
        except Exception as err:
            return [{
                'msg': err,
            }]

    def update_state(self, media: BaseMedia, key: str, value: Any):
        '''Update media state.
        '''
        try:
            return self.update_state_(media.path, key, value)
        except Exception as err:
            logger.error(err)
            return {
                'msg': err,
            }


class SqlModelFolderMixin(BaseFolderMixin):

    @classmethod
    def scan_media__(
        cls,
        medias: Optional[Generator[BaseMedia, None, None]]=None,
    ):
        logger.debug('scan_media__ medias: %s', medias)
        if medias is None:
            logger.warning('medias is None.')
            raise TypeError
        with cls.engine.get_session() as session:
            for media in medias:
                _media = models.Media(
                    title=media.title + '.' + media.ext,
                    md5=media.md5,
                    dirname=media.dirname,
                )
                session.add(_media)
            session.commit()
            return session.execute(select(models.Media)).all()

    @classmethod
    def update_state_(cls, path: str, key: str, value: Any):
        media: BaseMedia = cls.media__(path)
        with cls.engine.get_session() as session:
            # session.query(models.Media).filter(models.Media.md5 == media.md5).update({'created_at': datetime.now()})

            # statement = select(models.Media).where(models.Media.md5 == media.md5)
            # _media = session.execute(statement).first()

            _media: Optional[models.Media] = session.get(models.Media, media.md5)
            if _media is None:
                raise sqlalchemy.exc.NoResultFound(
                    f'No media with this md5 value was found in the database: {media.md5}')

            # Check has invalid keys.
            if key not in schemas.State.model_fields.keys():
                raise ValueError(f'Field state does not allow key: {key}.')

            _media.state[key] = value
            # logger.info(('media.state', type(_media.state), _media.state, _media.state.keys()))
            _media.state = schemas.State(**_media.state).model_dump()
            # logger.info(('media.path', type(_media.path), _media.path, key, _media.state.get(key)))

            # _media = models.Media.model_validate(_media)
            session.commit()
            return _media


class SqliteFolderMixin(BaseFolderMixin):
    _ENGINE_CLS = _sqlite.Engine
    engine: _ENGINE_CLS

    @classmethod
    def scan_media__(
        cls,
        medias: Optional[Generator[BaseMedia, None, None]]=None,
    ):
        if medias is None:
            logger.warning('medias is None.')
            raise TypeError
        cls.engine.execute_query(f"""
            CREATE TABLE IF NOT EXISTS {cls._DB_TABLE} (
                # id INT PRIMARY KEY default(random()),
                title TEXT UNIQUE,
                md5 TEXT NOT NULL UNIQUE,
                dirname TEXT,
                created_date TIMESTAMP,
                state JSON,
            )
        """)
        result_list: List[Any] = []
        for media in medias:
            result = cls.engine.execute_insert_update_delete(
                f"INSERT OR IGNORE INTO {cls._DB_TABLE} (title, md5, dirname, created_date) VALUES (?, ?, ?, ?)",
                (media.title + '.' + media.ext, media.md5, media.dirname, datetime.now()),
            )
            result_list.append(result)
        return result_list

    @classmethod
    def update_state_(cls, media: BaseMedia, key: str, value: Any):
        result = cls.engine.execute_query(f"SELECT * FROM {cls._DB_TABLE} WHERE md5 = ?", (media.md5, ))
        logger.info(('result', type(result), result, result[0][0], media.title + '.' + media.ext, media.md5))
        return cls.engine.execute_query(
            f"UPDATE {cls._DB_TABLE} SET state = json_set(state, '$.{key}', ?) WHERE md5 = ?", (value, media.md5))

    def query_state(self, path, media_type: str='video'):
        '''Query media state.
        '''
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(media_type, BaseMedia)
        media = MEDIA_CLS(path)
        return self._query_state(media)

    @classmethod
    def _query_state(cls, media: BaseMedia):
        result = cls.engine.execute_query(f"SELECT * FROM {cls._DB_TABLE} WHERE md5 = ?", (media.md5, ))
        logger.info(('result', type(result), result, result[0][0], media.title + '.' + media.ext, media.md5))
        return cls.engine.execute_query(
            f"SELECT title, json(state) FROM {cls._DB_TABLE} WHERE md5 = ?", (media.md5, ))


if __name__ == "__main__":
    # state = schemas.State()
    # logger.info(('state', type(state), state, state.dict()))
    # setattr(state, 'key', 'value')
    # logger.info(('state', type(state), state, state.dict()))
    _dict = {
        'key': 'value',
    }
    logger.info(('dict', type(_dict), _dict, _dict.keys(), 'key' in _dict, _dict['key'], hasattr(dict, 'key'), getattr(_dict, 'key', '233')))
