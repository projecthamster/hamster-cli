import datetime
import os
import pickle as pickle

import fauxfactory
import hamsterlib
import pytest
from click.testing import CliRunner
from pytest_factoryboy import register

import hamster_cli.hamster_cli as hamster_cli

from . import factories

try:
    from configparser import SafeConfigParser
except:
    from ConfigParser import SafeConfigParser

register(factories.CategoryFactory)
register(factories.ActivityFactory)
register(factories.FactFactory)


@pytest.fixture
def filename():
    return fauxfactory.gen_utf8()


@pytest.fixture
def filepath(tmpdir, filename):
    """Provide a fully qualified pathame within our tmp-dir."""
    return os.path.join(tmpdir.strpath, filename)


@pytest.fixture
def appdirs(mocker, tmpdir):
    """Provide mocked version specific user dirs using a tmpdir."""

    def ensure_directory_exists(directory):
        if not os.path.lexists(directory):
            os.makedirs(directory)
        return directory

    hamster_cli.AppDirs = mocker.MagicMock()
    hamster_cli.AppDirs.user_config_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('config').strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_data_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('data').strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_cache_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('cache').strpath, 'hamster_cli/'))
    hamster_cli.AppDirs.user_log_dir = ensure_directory_exists(os.path.join(
        tmpdir.mkdir('log').strpath, 'hamster_cli/'))
    return hamster_cli.AppDirs


@pytest.fixture
def runner(appdirs):
    """Used for integrations tests."""
    def runner(args=[]):
        return CliRunner().invoke(hamster_cli.run, args)
    return runner


@pytest.fixture
def base_config():
    """Provide a generic baseline configuration."""
    return lib_config, client_config


@pytest.fixture
def lib_config(tmpdir):
    """
    This is an actual config ficture, not config file.

    That means this fixture represents the the result of all typechecks and
    type conversions.
    """
    return {
        'work_dir': tmpdir.strpath,
        'store': 'sqlalchemy',
        'day_start': datetime.time(hour=0, minute=0, second=0),
        'db_path': 'sqlite:///:memory:',
        'tmpfile_name': 'test.pickle',
        'fact_min_delta': 60,
    }


@pytest.fixture
def client_config(tmpdir):
    """
    This is an actual config ficture, not config file.

    That means this fixture represents the the result of all typechecks and
    type conversions.
    """
    return {
        'work_dir': tmpdir.strpath,
        'unsorted_localized': 'Unsorted',
        'log_level': 10,
        'log_console': False,
        'logfile_path': False,
        'dbus': False,
    }


@pytest.fixture
def config_instance(tmpdir, faker):
    """
    This fixture provides a (dynamicly generated) SafeConfigParser instance.
    """
    def generate_config(**kwargs):
            config = SafeConfigParser()
            # Backend
            config.add_section('Backend')
            config.set('Backend', 'store', kwargs.get('store', 'sqlalchemy'))
            config.set('Backend', 'daystart', kwargs.get('daystart', '00:00:00'))
            config.set('Backend', 'db_path', kwargs.get('db_path', 'sqlite:////:memory:'))
            config.set('Backend', 'tmpfile_name', kwargs.get('tmpfile_name', 'test.pickle'))
            config.set('Backend', 'fact_min_delta', kwargs.get('fact_min_delta', '60'))
            config.set('Backend', 'db_engine', kwargs.get('db_engine', 'sqlite'))
            config.set('Backend', 'db_uri', kwargs.get('db_uri', 'hamster_cli.db'))
            config.set('Backend', 'db_user', kwargs.get('db_user', '')),
            config.set('Backend', 'db_password', kwargs.get('db_password', ''))

            # Client
            config.add_section('Client')
            config.set('Client', 'work_dir', kwargs.get('work_dir', tmpdir.strpath))
            config.set('Client', 'unsorted_localized', kwargs.get(
                'unsorted_localized', 'Unsorted'))
            config.set('Client', 'log_level', kwargs.get('log_level', 'debug'))
            config.set('Client', 'log_console', kwargs.get('log_console', '0'))
            config.set('Client', 'log_filename', kwargs.get('log_filename', faker.file_name()))
            config.set('Client', 'dbus', kwargs.get('dbus', '0'))
            return config
    return generate_config


@pytest.fixture
def config_file(config_instance, appdirs):
    """Provide a config file store under our fake config dir."""
    with open(os.path.join(appdirs.user_config_dir, 'hamster_cli.conf'), 'w') as fobj:
        config_instance().write(fobj)


@pytest.fixture
def tmp_fact(controler_with_logging, fact):
    fact.end = None
    fact = controler_with_logging.facts.save(fact)
    return fact


@pytest.fixture
def invalid_tmp_fact(tmpdir, client_config):
    with open(client_config['tmp_filename'], 'wb') as fobj:
        pickle.dump(None, fobj)


@pytest.yield_fixture
def controler(lib_config, client_config):
    controler = hamsterlib.HamsterControl(lib_config)
    controler.client_config = client_config
    yield controler
    if os.path.isfile(os.path.join(client_config['work_dir'],
            lib_config['tmpfile_name'])):
        os.remove(os.path.join(client_config['work_dir'],
            lib_config['tmpfile_name']))
    controler.store.cleanup()


@pytest.yield_fixture
def controler_with_logging(lib_config, client_config):
    controler = hamsterlib.HamsterControl(lib_config)
    controler.client_config = client_config
    # [FIXME]
    # We souldn't shortcut like this!
    hamster_cli._setup_logging(controler)
    yield controler
    if os.path.isfile(os.path.join(client_config['work_dir'],
            lib_config['tmpfile_name'])):
        os.remove(os.path.join(client_config['work_dir'],
            lib_config['tmpfile_name']))
    controler.store.cleanup()


@pytest.fixture(params=[
    ('', '', {
        'filter_term': '',
        'start': None,
        'end': None,
    }),
    ('', '2015-12-12 18:00 2015-12-12 19:30', {
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
    return request.param
