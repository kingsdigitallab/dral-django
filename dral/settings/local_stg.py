from .base import *  # noqa

ALLOWED_HOSTS = ['dral-stg.kdl.kcl.ac.uk']

CACHE_REDIS_DATABASE = '1'
CACHES['default']['LOCATION'] = '127.0.0.1:6379:' + CACHE_REDIS_DATABASE

INTERNAL_IPS = INTERNAL_IPS + ['']
ALLOWED_HOSTS = ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_dral_stg',
        'USER': 'app_dral',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
