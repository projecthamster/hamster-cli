import datetime
import pytest
import hamster_cli.hamster_cli as hamster_cli
import hamsterlib
from pytest_factoryboy import register
import factories
import pickle as pickle
import os
try:
    from configparser import SafeConfigParser
except:
    from ConfigParser import SafeConfigParser

register(factories.CategoryFactory)
register(factories.ActivityFactory)
register(factories.FactFactory)


@pytest.fixture
def runner():
    """Used for integrations tests."""
    def runner(args=[]):
        return testing.CliRunner().invoke(hamster_cli.run, args)
    return runner
@pytest.fixture
def base_config():
    return lib_config, client_config
    """Privide a generic baseline configuration."""

@pytest.fixture
def lib_config():
    return {
        'unsorted_localized': 'Unsorted',
        'store': 'sqlalchemy',
        'day_start': datetime.time(hour=0, minute=0, second=0),
        'day_end': datetime.time(hour=23, minute=59, second=59),
        'db-path': 'sqlite:///:memory:',
    }

@pytest.fixture
def client_config():
    """
    This is an actual config ficture, not config file.

    That means this fixture represents the the result of all typechecks and
    type conversions.
    """
    return {
        'cwd': '.',
        'tmp_filename': 'test_tmp_fact.pickle',
        'log_level': 10,
        'log_console': False,
        'log_file': False,
        'log_filename': False,
        'dbus': False,
    }

@pytest.fixture
def config_file(tmpdir, faker):
    def generate_config(**kwargs):
        path = os.path.join(tmpdir.strpath, 'test_config')
        with open(path, 'w') as fobj:
            config = SafeConfigParser()

            config.add_section('Client')
            config.set('Client', 'cwd', kwargs.get('cwd', '.'))
            config.set('Client', 'tmp_filename', kwargs.get('tmp_filename',
                'test_tmp_fact.pickle'))
            config.set('Client', 'log_level', kwargs.get('log_level', 'debug'))
            config.set('Client', 'log_console', kwargs.get('log_console', '0'))
            #config.set('Client', 'log_file', kwargs.get('log_file', '0'))
            config.set('Client', 'log_filename', kwargs.get('log_filename', faker.file_name()))
            config.set('Client', 'dbus', kwargs.get('dbus', '0'))

            config.add_section('Backend')
            config.set('Backend', 'unsorted_localized', kwargs.get(
                'unsorted_localized', 'Unsorted'))
            config.set('Backend', 'store', kwargs.get('store', 'sqlalchemy'))
            config.set('Backend', 'daystart', kwargs.get('daystart',
                '00:00:00'))
            config.set('Backend', 'dayend', kwargs.get('dayend',
                '23:59:59'))
            config.set('Backend', 'db_path', kwargs.get('db_path',
                'postgres://hamsterlib:foobar@localhost/hamsterlib'))
            config.write(fobj)
        return path
    return generate_config


@pytest.fixture
def tmp_fact(client_config, fact):
    with open(client_config['tmp_filename'], 'wb') as fobj:
        fact.end = None
        pickle.dump(fact, fobj)
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
    if os.path.isfile(os.path.join(client_config['cwd'], client_config['tmp_filename'])):
        os.remove(os.path.join(client_config['cwd'], client_config['tmp_filename']))
    controler.store.cleanup()


@pytest.yield_fixture
def controler_with_logging(lib_config, client_config):
    controler = hamsterlib.HamsterControl(lib_config)
    controler.client_config = client_config
    # [FIXME]
    # We souldn't shortcut like this!
    hamster_cli._setup_logging(controler)
    yield controler
    if os.path.isfile(os.path.join(client_config['cwd'], client_config['tmp_filename'])):
        os.remove(os.path.join(client_config['cwd'], client_config['tmp_filename']))
    controler.store.cleanup()
