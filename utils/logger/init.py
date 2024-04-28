import logging
import logging.config
import os

from config import CONFIG


ENV = os.getenv("ENV")
FORMATTER = "color" if ENV == "development" else "standard"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {
            "format": "%(asctime)s: [%(levelname)s]: %(name)s: %(message)s",
        },
        "standard": {
            "format": "%(asctime)s:[%(levelname)s]:%(pathname)s:%(lineno)d:%(funcName)s: %(message)s",
        },
        "color": {
            "class": "utils.logger.utils.ColorFormatter",
            "format": "[%(levelname)s]%(pathname)s:%(lineno)d:%(funcName)s: %(message)s",
        },
    },
    "filters": {
        "default": {"()": "utils.logger.utils.RelativePathFilter"},
        # "debug": {"()": "utils.logger.utils.RelativePathFilter"},
        # "info": {"()": "utils.logger.utils.RelativePathFilter"},
        # "warning": {"()": "utils.logger.utils.RelativePathFilter"},
        # "error": {"()": "utils.logger.utils.RelativePathFilter"},
        # "critical": {"()": "utils.logger.utils.RelativePathFilter"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            # Default is stderr
            # 'stream': 'ext://sys.stdout',
            # 'class': 'logging.StreamHandler',
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": f"{CONFIG.LOG_DIR}/default.log",
            "when": "midnight",
            "backupCount": 7,
            "encoding": "utf8",
            "filters": ["default"],
        },
        "console": {
            "level": "DEBUG",
            "formatter": FORMATTER,
            "class": "logging.StreamHandler",
            # Default is stderr
            "stream": "ext://sys.stdout",
            # 'filters': ['debug'],
        },
        "info": {
            "level": "INFO",
            "formatter": "standard",
            # Default is stderr
            "stream": "ext://sys.stdout",
            "class": "logging.StreamHandler",
            # 'class': 'logging.handlers.TimedRotatingFileHandler',
            # 'filename': f'{CONFIG.LOG_DIR}/info.log',
            # 'when': 'midnight',
            # 'backupCount': 2,
            # 'encoding': 'utf8',
            # 'filters': ['default'],
            # 'maxBytes': 5*1024*1024,
        },
        "warning": {
            "level": "WARNING",
            "formatter": "standard",
            # Default is stderr
            "stream": "ext://sys.stdout",
            "class": "logging.StreamHandler",
            # 'class': 'logging.handlers.TimedRotatingFileHandler',
            # 'filename': f'{CONFIG.LOG_DIR}/warning.log',
            # 'when': 'midnight',
            # 'backupCount': 7,
            # 'encoding': 'utf8',
            # 'filters': ['default'],
        },
        "error": {
            "formatter": "standard",
            "class": "logging.handlers.TimedRotatingFileHandler",
            # Default is stderr
            # 'stream': 'ext://sys.stdout',
            "filename": f"{CONFIG.LOG_DIR}/error.log",
            "when": "midnight",
            "backupCount": 7,
            "encoding": "utf8",
            "filters": ["default"],
        },
        "critical": {
            "level": "CRITICAL",
            "formatter": "standard",
            "class": "logging.handlers.TimedRotatingFileHandler",
            # Default is stderr
            # 'stream': 'ext://sys.stdout',
            "filename": f"{CONFIG.LOG_DIR}/critical.log",
            "when": "midnight",
            "backupCount": 7,
            "encoding": "utf8",
            "filters": ["default"],
        },
        "critical_mail": {
            "level": "CRITICAL",
            "formatter": "standard",
            "class": "logging.handlers.SMTPHandler",
            "mailhost": "localhost",
            "fromaddr": "xxx@domain.com",
            "toaddrs": ["xxx@domain.com", "xxx@domain.com"],
            "subject": "Critical error with application name",
            "filters": ["default"],
        },
    },
    "loggers": {
        # root logger
        "": {
            "handlers": [
                "default",
                "console",
                # 'info',
                # 'warning',
                # 'critical',
                # 'error',
            ],
            "level": CONFIG.LOG_LEVEL,
            "propagate": False,
        },
        "script": {"handlers": ["default"], "level": "INFO", "propagate": False},
        # if __name__ == '__main__'
        "__main__": {
            "handlers": ["default", "console", "info", "warning", "critical", "error"],
            "level": "DEBUG",
            "propagate": False,
        },
        "sqlalchemy": {
            "handlers": [
                "default",
                "console",
            ],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


logging.config.dictConfig(LOGGING_CONFIG)


if __name__ == "__main__":
    logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    logger.debug("Logging is configured.")
    logger.debug("log level: debug")
    logger.info("log level: info")
    logger.warning("log level: warning")
    logger.error("log level: error")
    logger.exception("log level: exception")
    logger.critical("log level: critical")
    logger.info({"a": 1, "b": "-" * 80, "c": {"d": 3, "e": 4, "f": {"g": 5, "h": 6}}})

    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.debug("sqlalchemy debug")
    sqlalchemy_logger.info("sqlalchemy info")
    sqlalchemy_logger.warning("sqlalchemy warning")
    sqlalchemy_logger.error(sqlalchemy_logger.__dict__)
