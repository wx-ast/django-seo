import logging
import re

from django.conf import settings
from django.db import models
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.contrib.contenttypes.models import ContentType


class NotSet(object):
    " A singleton to identify unset values (where None would have meaning) "
    def __str__(self):
        return "NotSet"
    def __repr__(self):
        return self.__str__()
NotSet = NotSet()


class Literal(object):
    " Wrap literal values so that the system knows to treat them that way "
    def __init__(self, value):
        self.value = value


class LazyList(list):
    """ Generic python list which is populated when items are first accessed.
    """

    def populate(self):
        """ Populates the list.
            This method must be overridden by subclasses.
            It is called once, when items in the list are first accessed.
        """
        raise NotImplementedError

    # Ensure list is only populated once
    def __init__(self, populate_function=None):
        if populate_function is not None:
            # TODO: Test this functionality!
            self.populate = populate_function
        self._populated = False

    def _populate(self):
        """ Populate this list by calling populate(), but only once. """
        if not self._populated:
            logging.debug("Populating lazy list %d (%s)" % (id(self), self.__class__.__name__))
            try:
                self.populate()
                self._populated = True
            except Exception as e:
                logging.debug("Currently unable to populate lazy list: %s" % e)

    # Accessing methods that require a populated field
    def __len__(self):
        self._populate()
        return super(LazyList, self).__len__()
    def __getitem__(self, key):
        self._populate()
        return super(LazyList, self).__getitem__(key)
    def __setitem__(self, key, value):
        self._populate()
        return super(LazyList, self).__setitem__(key, value)
    def __delitem__(self, key):
        self._populate()
        return super(LazyList, self).__delitem__(key)
    def __iter__(self):
        self._populate()
        return super(LazyList, self).__iter__()
    def __contains__(self, item):
        self._populate()
        return super(LazyList, self).__contains__(item)


class LazyChoices(LazyList):
    """ Allows a choices list to be given to Django model fields which is
        populated after the models have been defined (ie on validation).
    """

    def __bool__(self):
        # Django tests for existence too early, meaning population is attempted
        # before the models have been imported.
        # This may have some side effects if truth testing is supposed to
        # evaluate the list, but in the case of django choices, this is not
        # The case. This prevents __len__ from being called on truth tests.
        if not self._populated:
            return True
        else:
            return bool(len(self))


from django.urls import URLResolver, Resolver404, get_resolver
from django.urls.resolvers import URLPattern

def _pattern_resolve_to_name(pattern, path):
    match = get_regex(pattern).search(path)
    if match:
        name = ""
        if pattern.name:
            name = pattern.name
        elif hasattr(pattern, '_callback_str'):
            name = pattern._callback_str
        else:
            name = "%s.%s" % (pattern.callback.__module__, pattern.callback.__name__)
        return name

def get_regex(resolver_or_pattern):
     """Utility method for django's deprecated resolver.regex"""
     try:
         regex = resolver_or_pattern.regex
     except AttributeError:
         regex = resolver_or_pattern.pattern.regex
     return regex

def _resolver_resolve_to_name(resolver, path):
    tried = []
    match = get_regex(resolver).search(path)
    if match:
        new_path = path[match.end():]
        for pattern in resolver.url_patterns:
            try:
                if isinstance(pattern, URLResolver):
                    name = _resolver_resolve_to_name(pattern, new_path)
                elif isinstance(pattern, URLPattern):
                    name = _pattern_resolve_to_name(pattern, new_path)
            except Resolver404 as e:
                tried.extend([(get_regex(pattern).pattern + '   ' + t) for t in e.args[0]['tried']])
            else:
                if name:
                    return name
                tried.append(get_regex(pattern).pattern)
        raise Resolver404({'tried': tried, 'path': new_path})


def resolve_to_name(path, urlconf=None):
    try:
        return _resolver_resolve_to_name(get_resolver(urlconf), path)
    except Resolver404:
        return None


def _replace_quot(match):
    unescape = lambda v: v.replace('&quot;', '"').replace('&amp;', '&')
    return '<%s%s>' % (unescape(match.group(1)), unescape(match.group(3)))


def escape_tags(value, valid_tags):
    """ Strips text from the given html string, leaving only tags.
        This functionality requires BeautifulSoup, nothing will be
        done otherwise.

        This isn't perfect. Someone could put javascript in here:
              <a onClick="alert('hi');">test</a>

            So if you use valid_tags, you still need to trust your data entry.
            Or we could try:
              - only escape the non matching bits
              - use BeautifulSoup to understand the elements, escape everything else and remove potentially harmful attributes (onClick).
              - Remove this feature entirely. Half-escaping things securely is very difficult, developers should not be lured into a false sense of security.
    """
    # 1. escape everything
    value = conditional_escape(value)

    # 2. Reenable certain tags
    if valid_tags:
        # TODO: precompile somewhere once?
        tag_re = re.compile(r'&lt;(\s*/?\s*(%s))(.*?\s*)&gt;' % '|'.join(re.escape(tag) for tag in valid_tags))
        value = tag_re.sub(_replace_quot, value)

    # Allow comments to be hidden
    value = value.replace("&lt;!--", "<!--").replace("--&gt;", "-->")

    return mark_safe(value)


def _get_seo_content_types(seo_models):
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    try:
        return [ ContentType.objects.get_for_model(m).id for m in seo_models ]
    except: # previously caught DatabaseError
        # Return an empty list if this is called too early
        return []

def get_seo_content_types(seo_models):
    return lazy(_get_seo_content_types, list)(seo_models)
