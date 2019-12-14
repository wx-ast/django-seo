from rollyourown.seo.fields import Tag, MetaTag, KeywordTag, Raw
from rollyourown.seo.utils import Literal
from rollyourown.seo.base import MetadataBase
from django.db import models
from django.contrib.sites.models import Site

def get_site_name(metadata, **kwargs):
    return "example.com"

def get_model_instance_content(metadata, model_instance=None, **kwargs):
    if model_instance:
        return u'model instance content: %s' % model_instance.content
    return 'no model instance'

class Coverage(metaclass=MetadataBase):
    """ A SEO metadata definition, which should cover all configurable options.
    """
    def get_populate_from1(self, metadata, **kwargs):
        return "wxy"

    def get_populate_from2(self, metadata, **kwargs):
        return "xyz"
    get_populate_from2.short_description = "Always xyz"

    title        = Tag(populate_from=Literal("example.com"), head=True)
    heading      = Tag(max_length=68, name="hs:tag", verbose_name="tag two", head=True)

    keywords     = KeywordTag()
    description  = MetaTag(max_length=155, name="hs:metatag", verbose_name="metatag two")

    raw1         = Raw()
    raw2         = Raw(head=True, verbose_name="raw two", valid_tags=("meta", "title"))

    help_text1   = Tag(help_text="Some help text 1.")
    help_text2   = Tag(populate_from="def")
    help_text3   = Tag(populate_from=get_populate_from1, help_text="Some help text 3.")
    help_text4   = Tag(populate_from=get_populate_from2)
    help_text5   = Tag(populate_from="heading")
    help_text6   = Tag(populate_from="heading", help_text="Some help text 6.")

    populate_from1     = Tag(populate_from="get_populate_from1")
    populate_from2     = Tag(populate_from="heading")
    populate_from3     = Tag(populate_from=Literal("efg"))
    populate_from4     = Tag(populate_from="ghi")
    populate_from5     = Tag(populate_from="ghi", editable=False)
    populate_from6     = Tag(populate_from="keywords")
    populate_from7     = Tag(populate_from=get_model_instance_content)

    field1       = Tag(field=models.TextField)

    class Meta:
        verbose_name = "Basic Metadatum"
        verbose_name_plural = "Basic Metadata"
        use_sites = False
        groups = {
            'advanced': ('raw1', 'raw2' ),
            'help_text': ( 'help_text1', 'help_text2', 'help_text3', 'help_text4', )
        }
        seo_models = ('userapp', )
        seo_views = ('userapp', )

    class HelpText:
        help_text2 = "Updated help text2."


class WithSites(metaclass=MetadataBase):
    title        = Tag()

    class Meta:
        use_sites = True

class WithI18n(metaclass=MetadataBase):
    title        = Tag()

    class Meta:
        use_i18n = True

class WithRedirect(metaclass=MetadataBase):
    title        = Tag()

    class Meta:
        use_redirect = True

class WithRedirectSites(metaclass=MetadataBase):
    title        = Tag()

    class Meta:
        use_sites = True
        use_redirect = True

class WithCache(metaclass=MetadataBase):
    title    = Tag(head=True, populate_from=Literal("1234"))
    subtitle = Tag(head=True)

    class Meta:
        use_cache = True

class WithCacheSites(metaclass=MetadataBase):
    title    = Tag(head=True, populate_from=Literal("1234"))
    subtitle = Tag(head=True)

    class Meta:
        use_cache = True
        use_sites = True

class WithCacheI18n(metaclass=MetadataBase):
    title    = Tag(head=True, populate_from=Literal("1234"))
    subtitle = Tag(head=True)

    class Meta:
        use_cache = True
        use_i18n = True

class WithBackends(metaclass=MetadataBase):
    title    = Tag()

    class Meta:
        backends = ('view', 'path')

class WithSEOModels(metaclass=MetadataBase):
    title = Tag()

    class Meta:
        seo_models = ('userapp', )
