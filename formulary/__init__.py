"""
Formulary: Cloud-Formation Stack Management

"""
__version__ = '0.1.1'

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'incremental': False,
    'formatters': {
        'console': {
            'format': (
                '%(levelname)-8s %(name) -24s: %(message)s'
            )
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'loggers': {
        'boto': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'formulary': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}

