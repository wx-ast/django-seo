VERSION = (1, 0, 2, 'beta', 1)
__authors__ = ["Will Hardy <django-seo@willhardy.com.au>"]


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3:] == ('alpha', 0):
        version = '%s pre-alpha' % version
    elif VERSION[3] != 'final':
        version = '%s %s %s' % (version, VERSION[3], VERSION[4])
    return version
__version__ = get_version()

default_app_config = 'rollyourown.seo.apps.SeoConfig'
