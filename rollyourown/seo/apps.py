from django.apps.config import AppConfig
from rollyourown.seo.models import setup


class SeoConfig(AppConfig):
    name = 'rollyourown.seo'
    verbose_name = 'DjangoSEO'

    def ready(self):
        setup()
