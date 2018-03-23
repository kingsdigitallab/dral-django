from .base import *  # noqa

DEBUG = True

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'dral',
        'USER': 'dral',
        'PASSWORD': 'dral',
        'ADMINUSER': 'postgres',
        'HOST': 'localhost'
    },
}

# 10.0.2.2 is the default IP for the VirtualBox Host machine
INTERNAL_IPS = ['0.0.0.0', '127.0.0.1', '::1', '10.0.2.2']

SECRET_KEY = '12345'

FABRIC_USER = ''

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_auth_ldap.backend.LDAPBackend',
)

# -----------------------------------------------------------------------------
# Django Debug Toolbar
# http://django-debug-toolbar.readthedocs.org/en/latest/
# -----------------------------------------------------------------------------

try:
    import debug_toolbar  # noqa

    INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware']
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
except ImportError:
    pass

LOGGING['loggers']['dral'] = {}
LOGGING['loggers']['dral']['handlers'] = ['console']
LOGGING['loggers']['dral']['level'] = logging.DEBUG


