import os

from setuptools import find_packages, setup


setup(
    name = 'django-seo',
    zip_safe = False,  # eggs are the devil.
    version = '1.0.2',
    description = 'A framework for managing SEO metadata in Django.',
    long_description = open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    author = 'Will Hardy',
    author_email = 'djangoseo@willhardy.com.au',
    url = 'https://github.com/wx-ast/django-seo',
    include_package_data = True,
    packages = find_packages(exclude=['docs*', 'regressiontests*']),

    namespace_packages = ['rollyourown'],
    requires = ['django (>=2.2)'],
    license = 'LICENSE',
    keywords = 'seo, django, framework',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: Apache Software License',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    python_requires='>=3.6',
)

