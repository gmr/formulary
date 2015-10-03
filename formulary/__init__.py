"""
Formulary: Cloud-Formation Stack Management

"""
__version__ = '0.4.0'

LOG_WARNING = {
    'version': 1,
    'disable_existing_loggers': True,
    'incremental': False,
    'formatters': {
        'console': {'format': ('%(levelname)-8s %(module) -30s %(message)s')},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'console'},
    },
    'loggers': {
        'boto3': {'handlers': ['console'],'level': 'WARNING'},
        'formulary': {'handlers': ['console'], 'level': 'WARNING'},
        'troposphere': {'handlers': ['console'], 'level': 'WARNING'}
    }
}

LOG_DEBUG = dict(LOG_WARNING)
LOG_INFO = dict(LOG_WARNING)
for key in LOG_WARNING['loggers']:
    LOG_DEBUG['loggers'][key]['level'] = 'DEBUG'
    LOG_INFO['loggers'][key]['level'] = 'INFO'
