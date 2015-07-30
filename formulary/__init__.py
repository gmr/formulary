"""
Formulary: Cloud-Formation Stack Management

"""
__version__ = '0.3.6'

DEBUG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'incremental': False,
    'formatters': {
        'console': {
            'format': (
                '%(levelname)-8s %(name) -30s %(message)s'
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
        'boto3': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'formulary': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}


LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'incremental': False,
    'formatters': {
        'console': {
            'format': (
                '%(levelname)-8s %(module) -30s %(message)s'
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
        'boto3': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'formulary': {
            'handlers': ['console'],
            'level': 'WARNING',
        }
    }
}

