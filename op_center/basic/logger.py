import logging.config

DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(levelname)-8s %(name)s %(message)s",
        },
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ["default", "console"]
        },
        'test': {
            'level': 'DEBUG',
            'handlers': ["test", "console"]
        },
    },
    "handlers": {
        "workflow": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simple",
            "filename": "logs/workflow.log",
            "maxBytes": 10240000000,
            "backupCount": 7,
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "test": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "logs/test.log",
            "maxBytes": 10240000000,
            "backupCount": 7,
        },
        "default": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "logs/opcenter.log",
            "maxBytes": 10240000000,
            "backupCount": 7,
        },
    }
}
