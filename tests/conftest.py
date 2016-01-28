import datetime
import pytest
import hamster_cli.hamster_cli as hamster_cli
import hamsterlib
from pytest_factoryboy import register
import factories

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


@pytest.yield_fixture
def controler(lib_config, client_config):
    controler = hamsterlib.HamsterControl(lib_config)
    controler.client_config = client_config
    # [FIXME]
    # We souldn't shortcut like this!
    hamster_cli._setup_logging(controler)
    yield controler
    controler.store.cleanup()
