"""
Fixtures available in our tests.

In general fixtures shoudl return a single instance. If a fixture is a factory its name should
reflect that. Fixtures that are parametrized should be suffixed with ``_parametrized`` to indicate
the potentially increased costs to it.
"""

from __future__ import absolute_import, unicode_literals

import codecs
import datetime
import os
import pickle as pickle

import fauxfactory
import hamster_lib
import pytest
# Once we drop py2 support, we can use the builtin again but unicode support
# under python 2 is practicly non existing and manual encoding is not easily
# possible.
from backports.configparser import SafeConfigParser
from click.testing import CliRunner
from pytest_factoryboy import register
from six import text_type

import hamster_cli.hamster_cli as hamster_cli

from . import factories

register(factories.CategoryFactory)
register(factories.ActivityFactory)
register(factories.FactFactory)


@pytest.fixture
def filename():
    """Provide a filename string."""
    return fauxfactory.gen_utf8()


@pytest.fixture
def filepath(tmpdir, filename):
    """Provide a fully qualified pathame within our tmp-dir."""
    return os.path.join(tmpdir.strpath, filename)


@pytest.fixture
def appdirs(mocker, tmpdir):
    """
    Provide mocked version specific user dirs using a tmpdir.

    We add a utf8-subdir to our paths to make sure our consuming methods can cope with it.
    """
    def ensure_directory_exists(directory):
        if not os.path.lexists(directory):
            os.makedirs(directory)
        return directory

    hamster_cli.AppDirs = mocker.MagicMock()
    hamster_cli.AppDirs.user_config_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('config').mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_data_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('data').mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_cache_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('cache').mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_log_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('log').mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_cli/'))
    return hamster_cli.AppDirs


@pytest.fixture
def runner(appdirs, get_config_file):
    """Provide a convenient fixture to simulate execution of (sub-) commands."""
    def runner(args=[], **kwargs):
        return CliRunner().invoke(hamster_cli.run, args, **kwargs)
    return runner


@pytest.fixture
def base_config():
    """Provide a generic baseline configuration."""
    return lib_config, client_config


@pytest.fixture
def lib_config(tmpdir):
    """
    Provide a backend config fixture. This can be passed to a controler directly.

    That means this fixture represents the the result of all typechecks and
    type conversions.
    """
    return {
        'store': 'sqlalchemy',
        'day_start': datetime.time(hour=0, minute=0, second=0),
        'db_engine': 'sqlite',
        'db_path': ':memory:',
        'tmpfile_path': os.path.join(tmpdir.mkdir(fauxfactory.gen_utf8()).strpath, 'test.pickle'),
        'fact_min_delta': 60,
    }


@pytest.fixture
def client_config(tmpdir):
    """
    Provide a client config fixture. This can be passed to a controler directly.

    That means this fixture represents the the result of all typechecks and
    type conversions.
    """
    return {
        'unsorted_localized': 'Unsorted',
        'log_level': 10,
        'log_console': False,
        'logfile_path': False,
        'export_path': os.path.join(
            tmpdir.mkdir('export').mkdir(fauxfactory.gen_utf8()).strpath, 'export'),
        'logging_path': os.path.join(
            tmpdir.mkdir('log2').mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_cli.log'),
    }


@pytest.fixture
def config_instance(tmpdir, faker):
    """Provide a (dynamicly generated) SafeConfigParser instance."""
    def generate_config(**kwargs):
            config = SafeConfigParser()
            # Backend
            config.add_section('Backend')
            config.set('Backend', 'store', kwargs.get('store', 'sqlalchemy'))
            config.set('Backend', 'daystart', kwargs.get('daystart', '00:00:00'))
            config.set('Backend', 'fact_min_delta', kwargs.get('fact_min_delta', '60'))
            config.set('Backend', 'db_engine', kwargs.get('db_engine', 'sqlite'))
            config.set('Backend', 'db_path', kwargs.get('db_path', os.path.join(
                tmpdir.mkdir(fauxfactory.gen_utf8()).strpath, 'hamster_db.sqlite')))
            config.set('Backend', 'db_host', kwargs.get('db_host', ''))
            config.set('Backend', 'db_name', kwargs.get('db_name', ''))
            config.set('Backend', 'db_port', kwargs.get('db_port', ''))
            config.set('Backend', 'db_user', kwargs.get('db_user', '')),
            config.set('Backend', 'db_password', kwargs.get('db_password', ''))

            # Client
            config.add_section('Client')
            config.set('Client', 'unsorted_localized', kwargs.get(
                'unsorted_localized', 'Unsorted'))
            config.set('Client', 'log_level', kwargs.get('log_level', 'debug'))
            config.set('Client', 'log_console', kwargs.get('log_console', '0'))
            config.set('Client', 'log_filename', kwargs.get('log_filename', faker.file_name()))
            return config
    return generate_config


@pytest.fixture
def config_file(config_instance, appdirs):
    """Provide a config file store under our fake config dir."""
    with codecs.open(os.path.join(appdirs.user_config_dir, 'hamster_cli.conf'),
            'w', encoding='utf-8') as fobj:
        config_instance().write(fobj)


@pytest.fixture
def get_config_file(config_instance, appdirs):
    """Provide a dynamic config file store under our fake config dir."""
    def generate(**kwargs):
        instance = config_instance(**kwargs)
        with codecs.open(os.path.join(appdirs.user_config_dir, 'hamster_cli.conf'),
                'w', encoding='utf-8') as fobj:
            instance.write(fobj)
        return instance
    return generate


# Various config settings
@pytest.fixture
def db_name(request):
    """Return a randomized database name."""
    return fauxfactory.gen_utf8()


@pytest.fixture
def db_user(request):
    """Return a randomized database username."""
    return fauxfactory.gen_utf8()


@pytest.fixture
def db_password(request):
    """Return a randomized database password."""
    return fauxfactory.gen_utf8()


@pytest.fixture(params=(fauxfactory.gen_latin1(), fauxfactory.gen_ipaddr()))
def db_host(request):
    """Return a randomized database username."""
    return request.param


@pytest.fixture
def db_port(request):
    """Return a randomized database port."""
    return text_type(fauxfactory.gen_integer(min_value=0, max_value=65535))


@pytest.fixture
def tmp_fact(controler_with_logging, fact):
    """Fixture that ensures there is a ``ongoing fact`` file present at the expected place."""
    fact.end = None
    fact = controler_with_logging.facts.save(fact)
    return fact


@pytest.fixture
def invalid_tmp_fact(tmpdir, client_config):
    """Fixture to provide a *ongoing fact* file that contains an invalid object instance."""
    with open(client_config['tmp_filename'], 'wb') as fobj:
        pickle.dump(None, fobj)


@pytest.yield_fixture
def controler(lib_config, client_config):
    """Provide a pseudo controler instance."""
    controler = hamster_lib.HamsterControl(lib_config)
    controler.client_config = client_config
    yield controler
    controler.store.cleanup()


@pytest.yield_fixture
def controler_with_logging(lib_config, client_config):
    """Provide a pseudo controler instance with logging setup."""
    controler = hamster_lib.HamsterControl(lib_config)
    controler.client_config = client_config
    # [FIXME]
    # We souldn't shortcut like this!
    hamster_cli._setup_logging(controler)
    yield controler
    controler.store.cleanup()


@pytest.fixture(params=[
    ('', '', {
        'filter_term': '',
        'start': None,
        'end': None,
    }),
    ('', '2015-12-12 18:00 - 2015-12-12 19:30', {
        'filter_term': '',
        'start': datetime.datetime(2015, 12, 12, 18, 0, 0),
        'end': datetime.datetime(2015, 12, 12, 19, 30, 0)
    }),
    ('', '2015-12-12 18:00', {
        'filter_term': '',
        'start': datetime.datetime(2015, 12, 12, 18, 0, 0),
        'end': datetime.datetime(2015, 12, 12, 23, 59, 59)
    }),
    ('', '2015-12-12', {
        'filter_term': '',
        'start': datetime.datetime(2015, 12, 12, 0, 0, 0),
        'end': datetime.datetime(2015, 12, 12, 23, 59, 59)
    }),
    ('', '13:00', {
        'filter_term': '',
        'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
        'end': datetime.datetime(2015, 12, 12, 23, 59, 59),
    }),
])
def search_parameter_parametrized(request):
    """Provide a parametrized set of arguments for the ``search`` command."""
    return request.param
