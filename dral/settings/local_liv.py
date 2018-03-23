from .base import *  # noqa

ALLOWED_HOSTS = ['dral.kdl.kcl.ac.uk']

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_dral_liv',
        'USER': 'app_dral',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
