#!/usr/bin/env python
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey
from django.template import Template, Context
from django.utils import six

from rollyourown.seo.utils import resolve_to_name, NotSet, Literal

RESERVED_FIELD_NAMES = ('_metadata', '_path', '_content_type', '_object_id',
                        '_content_object', '_view', '_site', 'objects',
                        '_resolve_value', '_set_context', 'id', 'pk' )

SEO_PATH_FIELD_MAX_LENGTH = getattr(settings, 'SEO_PATH_FIELD_MAX_LENGTH', 255)

backend_registry = OrderedDict()

class MetadataBaseModel(models.Model):

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(MetadataBaseModel, self).__init__(*args, **kwargs)

        # Provide access to a class instance
        # TODO Rename to __metadata
        self._metadata = self.__class__._metadata()

    # TODO Rename to __resolve_value?
    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. """
        name = str(name)
        if name in self._metadata._meta.elements:
            element = self._metadata._meta.elements[name]

            # Look in instances for an explicit value
            if element.editable:
                value = getattr(self, name)
                if value:
                    return value

            # Otherwise, return an appropriate default value (populate_from)
            populate_from = element.populate_from
            if callable(populate_from):
                return populate_from(self, **self._populate_from_kwargs())
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

        # If this is not an element, look for an attribute on metadata
        try:
            value = getattr(self._metadata, name)
        except AttributeError:
            pass
        else:
            if callable(value):
                if getattr(value, 'im_self', None):
                    return value(self)
                else:
                    return value(self._metadata, self)
            return value

    def _populate_from_kwargs(self):
        return {}


class BaseManager(models.Manager):
    def on_current_site(self, site=None):
        if isinstance(site, Site):
            site_id = site.id
        elif site is not None:
            site_id = site and Site.objects.get(domain=site).id
        else:
            site_id = settings.SITE_ID
        # Exclude entries for other sites
        where = ['_site_id IS NULL OR _site_id=%s']
        return self.get_queryset().extra(where=where, params=[site_id])

    def for_site_and_language(self, site=None, language=None):
        queryset = self.on_current_site(site)
        if language:
            queryset = queryset.filter(_language=language)
        return queryset

# Following is part of an incomplete move to define backends, which will:
#   -  contain the business logic of backends to a short, succinct module
#   -  allow individual backends to be turned on and off
#   -  allow new backends to be added by end developers
#
# A Backend:
#   -  defines an abstract base class for storing the information required to associate metadata with its target (ie a view, a path, a model instance etc)
#   -  defines a method for retrieving an instance
#
# This is not particularly easy.
#   -  unique_together fields need to be defined in the same django model, as some django versions don't enforce the uniqueness when it spans subclasses
#   -  most backends use the path to find a matching instance. The model backend however ideally needs a content_type (found from a model instance backend, which used the path)
#   -  catering for all the possible options (use_sites, use_languages), needs to be done succiently, and at compile time
#
# This means that:
#   -  all fields that share uniqueness (backend fields, _site, _language) need to be defined in the same model
#   -  as backends should have full control over the model, therefore every backend needs to define the compulsory fields themselves (eg _site and _language).
#      There is no way to add future compulsory fields to all backends without editing each backend individually.
#      This is probably going to have to be a limitataion we need to live with.

class MetadataBackendBase(type):

    def __new__(cls, name, bases, attrs):
        new_class = type.__new__(cls, name, bases, attrs)
        backend_registry[new_class.name] = new_class
        return new_class


class MetadataBackend(six.with_metaclass(MetadataBackendBase)):
    name = None
    verbose_name = None
    unique_together = None


    def get_unique_together(self, options):
        ut = []
        for ut_set in self.unique_together:
            ut_set = [a for a in ut_set]
            if options.use_sites:
                ut_set.append('_site')
            if options.use_i18n:
                ut_set.append('_language')
            if len(ut_set) > 1:
                ut.append(tuple(ut_set))
        return tuple(ut)

    def get_manager(self, options):
        _get_instances = self.get_instances

        class _Manager(BaseManager):
            def get_instances(self, path, site=None, language=None, context=None):
                queryset = self.for_site_and_language(site, language)
                return _get_instances(queryset, path, context)

            if not options.use_sites:
                def for_site_and_language(self, site=None, language=None):
                    queryset = self.get_queryset()
                    if language:
                        queryset = queryset.filter(_language=language)
                    return queryset
        return _Manager


    @staticmethod
    def validate(options):
        """ Validates the application of this backend to a given metadata
        """


class PathBackend(MetadataBackend):
    name = "path"
    verbose_name = "Path"
    unique_together = (("_path",),)

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class PathMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=SEO_PATH_FIELD_MAX_LENGTH, unique=not (options.use_sites or options.use_i18n))
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"), on_delete=models.CASCADE)
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def __str__(self):
                return self._path

            def _populate_from_kwargs(self):
                return {'path': self._path}

            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return PathMetadataBase


class ViewBackend(MetadataBackend):
    name = "view"
    verbose_name = "View"
    unique_together = (("_view",),)

    def get_instances(self, queryset, path, context):
        view_name = ""
        if path is not None:
            view_name = resolve_to_name(path)
        return queryset.filter(_view=view_name or "")

    def get_model(self, options):
        class ViewMetadataBase(MetadataBaseModel):
            _view = models.CharField(_('view'), max_length=255, unique=not (options.use_sites or options.use_i18n), default="", blank=True)
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"), on_delete=models.CASCADE)
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def _process_context(self, context):
                """ Use the context when rendering any substitutions.  """
                if 'view_context' in context:
                    self.__context = context['view_context']

            def _populate_from_kwargs(self):
                return {'view_name': self._view}

            def _resolve_value(self, name):
                value = super(ViewMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, context=self.__context)
                except AttributeError:
                    return value

            def __str__(self):
                return self._view

            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return ViewMetadataBase


class ModelInstanceBackend(MetadataBackend):
    name = "modelinstance"
    verbose_name = "Model Instance"
    unique_together = (("_path",), ("_content_type", "_object_id"))

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class ModelInstanceMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=SEO_PATH_FIELD_MAX_LENGTH, editable=False, unique=not (options.use_sites or options.use_i18n))
            _content_type = models.ForeignKey(ContentType, editable=False, on_delete=models.CASCADE)
            _object_id = models.PositiveIntegerField(editable=False)
            _content_object = GenericForeignKey('_content_type', '_object_id')
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"), on_delete=models.CASCADE)
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def __str__(self):
                return self._path

            class Meta:
                unique_together = self.get_unique_together(options)
                abstract = True

            def _process_context(self, context):
                context['content_type'] = self._content_type
                context['model_instance'] = self

            def _populate_from_kwargs(self):
                return {'model_instance': self._content_object}

            def save(self, *args, **kwargs):
                try:
                    path_func = self._content_object.get_absolute_url
                except AttributeError:
                    pass
                else:
                    self._path = path_func()
                super(ModelInstanceMetadataBase, self).save(*args, **kwargs)

        return ModelInstanceMetadataBase


class ModelBackend(MetadataBackend):
    name = "model"
    verbose_name = "Model"
    unique_together = (("_content_type",),)

    def get_instances(self, queryset, path, context):
        if context and 'content_type' in context:
            return queryset.filter(_content_type=context['content_type'])

    def get_model(self, options):
        class ModelMetadataBase(MetadataBaseModel):
            _content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"), on_delete=models.CASCADE)
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def __str__(self):
                return six.u(str(self._content_type))

            def _process_context(self, context):
                """ Use the given model instance as context for rendering
                    any substitutions.
                """
                if 'model_instance' in context:
                    self.__instance = context['model_instance']

            def _populate_from_kwargs(self):
                return {'content_type': self._content_type}

            def _resolve_value(self, name):
                value = super(ModelMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, self.__instance._content_object)
                except AttributeError:
                    return value

            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)
        return ModelMetadataBase

    @staticmethod
    def validate(options):
        """ Validates the application of this backend to a given metadata
        """
        try:
            if options.backends.index('modelinstance') > options.backends.index('model'):
                raise Exception("Metadata backend 'modelinstance' must come before 'model' backend")
        except ValueError:
            raise Exception("Metadata backend 'modelinstance' must be installed in order to use 'model' backend")



def _resolve(value, model_instance=None, context=None):
    """ Resolves any template references in the given value.
    """

    if isinstance(value, six.string_types) and "{" in value:
        if context is None:
            context = Context()
        if model_instance is not None:
            context[model_instance._meta.module_name] = model_instance
        value = Template(value).render(context)
    return value

