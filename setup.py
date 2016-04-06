#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'Click',
    'tabulate',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='hamster_cli',
    version='0.0.1',
    description="A basic CLI for the hamster time tracker.",
    long_description=readme + '\n\n' + history,
    author="Eric Goller",
    author_email='Elbenfreund@DenkenInEchtzeit.net',
    url='https://github.com/elbenfreund/hamster_cli',
    packages=[
        'hamster_cli',
    ],
    package_dir={'hamster_cli':
                 'hamster_cli'},
    #include_package_data=True,
    install_requires=requirements,
    license="GPL3",
    zip_safe=False,
    keywords='hamster_cli',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPL3',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points='''
    [console_scripts]
    hamsterlib-cli=hamster_cli.hamster_cli:run
    ''',
)
