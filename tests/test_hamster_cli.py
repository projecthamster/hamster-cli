# -*- coding: utf-8 -*-

import datetime
import logging
import os

import fauxfactory
import hamsterlib
import pytest
# Once we drop py2 support, we can use the builtin again but unicode support
# under python 2 is practicly non existing and manual encoding is not easily
# possible.
from backports.configparser import SafeConfigParser
from click import ClickException
from freezegun import freeze_time

from hamster_cli import hamster_cli


class TestSearch(object):
    """Unit tests for search command."""

    @freeze_time('2015-12-12 18:00')
    def test_search(self, controler, mocker, fact, search_parameter_parametrized):
        """Ensure that your search parameters get passed on to the apropiate backend function."""
        search_term, time_range, expectation = search_parameter_parametrized
        controler.facts.get_all = mocker.MagicMock(return_value=[fact])
        hamster_cli._search(controler, search_term, time_range)
        controler.facts.get_all.assert_called_with(**expectation)


class TestStart(object):
    """Unit test related to starting a new fact."""

    @pytest.mark.parametrize(('raw_fact', 'start', 'end', 'expectation'), [
        ('foo@bar', '2015-12-12 13:00', '2015-12-12 16:30', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 16, 30, 0),
        }),
        ('10:00-18:00 foo@bar', '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': datetime.datetime(2015, 12, 25, 18, 00, 0),
        }),
        # 'ongoing fact's
        ('foo@bar', '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': None,
        }),
        ('11:00 foo@bar', '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': None,
        }),
    ])
    @freeze_time('2015-12-25 18:00')
    def test_start_add_new_fact(self, controler_with_logging, mocker, raw_fact,
            start, end, expectation):
        """
        Test that inpul validation and assignment of start/endtime works is done as expected.
        """
        controler = controler_with_logging
        controler.facts.save = mocker.MagicMock()
        hamster_cli._start(controler, raw_fact, start, end)
        assert controler.facts.save.called
        args, kwargs = controler.facts.save.call_args
        fact = args[0]
        assert fact.start == expectation['start']
        assert fact.end == expectation['end']
        assert fact.activity.name == expectation['activity']
        assert fact.category.name == expectation['category']


class TestStop(object):
    """Unit test concerning the stop command."""

    def test_stop_existing_tmp_fact(self, tmp_fact, controler_with_logging, mocker):
        """Make sure stoping an ongoing fact works as intended."""
        controler_with_logging.facts.stop_tmp_fact = mocker.MagicMock()
        hamster_cli._stop(controler_with_logging)
        assert controler_with_logging.facts.stop_tmp_fact.called

    def test_stop_no_existing_tmp_fact(self, controler_with_logging, capsys):
        """Make sure that stop without actually an ongoing fact leads to an error."""
        controler = controler_with_logging
        with pytest.raises(ClickException):
            hamster_cli._stop(controler)
            out, err = capsys.readouterr()
            assert 'Unable to continue' in err


class TestCancel(object):
    """Unit tests related to cancelation of an ongoing fact."""

    def test_cancel_existing_tmp_fact(self, tmp_fact, controler_with_logging, mocker,
            capsys):
        """Test cancelation in case there is an ongoing fact."""
        controler = controler_with_logging
        controler.facts.cancel_tmp_fact = mocker.MagicMock(return_value=None)
        hamster_cli._cancel(controler)
        out, err = capsys.readouterr()
        assert controler.facts.cancel_tmp_fact.called
        assert 'canceled' in out

    def test_cancel_no_existing_tmp_fact(self, controler_with_logging, capsys):
        """Test cancelation in case there is no actual ongoing fact."""
        with pytest.raises(ClickException):
            hamster_cli._cancel(controler_with_logging)
            out, err = capsys.readouterr()
            assert 'Nothing tracked right now' in err


class TestExport(object):
    """Unittests related to data export."""
    @pytest.mark.parametrize('format', ['html', fauxfactory.gen_latin1()])
    def test_invalid_format(self, controler_with_logging, format, mocker):
        """Make sure that passing an invalid format exits prematurely."""
        controler = controler_with_logging
        with pytest.raises(ClickException):
            hamster_cli._export(controler, format, None, None)

    def test_csv(self, controler, controler_with_logging, mocker):
        """Make sure that a valid format returns the apropiate writer class."""
        hamsterlib.reports.TSVWriter = mocker.MagicMock()
        hamster_cli._export(controler, 'csv', None, None)
        assert hamsterlib.reports.TSVWriter.called

    def test_ical(self, controler, controler_with_logging, mocker):
        """Make sure that a valid format returns the apropiate writer class."""
        hamsterlib.reports.ICALWriter = mocker.MagicMock()
        hamster_cli._export(controler, 'ical', None, None)
        assert hamsterlib.reports.ICALWriter.called

    def test_xml(self, controler, controler_with_logging, mocker):
        """Make sure that passing 'xml' as format parameter returns the apropiate writer class."""
        hamsterlib.reports.XMLWriter = mocker.MagicMock()
        hamster_cli._export(controler, 'xml', None, None)
        assert hamsterlib.reports.XMLWriter.called

    def test_with_start(self, controler, controler_with_logging, tmpdir, mocker):
        """Make sure that passing a end date is passed to the fact gathering method."""
        controler.facts.get_all = mocker.MagicMock()
        path = os.path.join(tmpdir.mkdir('report').strpath, 'report.csv')
        hamsterlib.reports.TSVWriter = mocker.MagicMock(return_value=hamsterlib.reports.TSVWriter(
            path))
        start = fauxfactory.gen_datetime()
        hamster_cli._export(controler, 'csv', start, None)
        args, kwargs = controler.facts.get_all.call_args
        assert kwargs['start'] == start

    def test_with_end(self, controler, controler_with_logging, tmpdir, mocker):
        """Make sure that passing a end date is passed to the fact gathering method."""
        controler.facts.get_all = mocker.MagicMock()
        path = os.path.join(tmpdir.mkdir('report').strpath, 'report.csv')
        hamsterlib.reports.TSVWriter = mocker.MagicMock(return_value=hamsterlib.reports.TSVWriter(
            path))
        end = fauxfactory.gen_datetime()
        hamster_cli._export(controler, 'csv', None, end)
        args, kwargs = controler.facts.get_all.call_args
        assert kwargs['end'] == end


class TestCategories(object):
    """Unittest related to category listings."""

    def test_categories(self, controler_with_logging, category, mocker, capsys):
        """Make sure the categories get displayed to the user."""
        controler = controler_with_logging
        controler.categories.get_all = mocker.MagicMock(return_value=[category])
        hamster_cli._categories(controler)
        out, err = capsys.readouterr()
        assert category.name in out
        assert controler.categories.get_all.called


class TestCurrent(object):
    """Unittest for dealing with 'ongoing facts'."""

    def test_tmp_fact(self, controler, tmp_fact, controler_with_logging, capsys, fact, mocker):
        """Make sure the current fact is displayed if there is one."""
        controler = controler_with_logging
        controler.facts.get_tmp_fact = mocker.MagicMock(return_value=fact)
        hamster_cli._current(controler)
        out, err = capsys.readouterr()
        assert controler.facts.get_tmp_fact
        assert str(fact) in out

    def test_no_tmp_fact(self, controler_with_logging, capsys):
        """Make sure we display proper feedback if there is no current 'ongoing fact."""
        controler = controler_with_logging
        with pytest.raises(ClickException):
            hamster_cli._current(controler)
            out, err = capsys.readouterr()
            assert 'There seems no be no activity beeing tracked right now' in err


class TestActivities(object):
    """Unittests for the ``activities`` command."""

    def test_activities_no_category(self, controler, activity, mocker, capsys):
        """Make sure command works if activities do not have a category associated."""
        activity.category = None
        controler.activities.get_all = mocker.MagicMock(
            return_value=[activity])
        mocker.patch('hamster_cli.hamster_cli.tabulate')
        hamster_cli.tabulate = mocker.MagicMock(
            return_value='{}, {}'.format(activity.name, None))
        hamster_cli._activities(controler, '')
        out, err = capsys.readouterr()
        assert activity.name in out
        hamster_cli.tabulate.call_args[0] == [(activity.name, None)]

    def test_activities_with_category(self, controler, activity, mocker,
            capsys):
        """Make sure activity name and category are displayed if present."""
        controler.activities.get_all = mocker.MagicMock(
            return_value=[activity])
        hamster_cli._activities(controler, '')
        out, err = capsys.readouterr()
        assert activity.name in out
        assert activity.category.name in out

    def test_activities_with_search_term(self, controler, activity, mocker,
            capsys):
        """Make sure the search term is passed on."""
        controler.activities.get_all = mocker.MagicMock(
            return_value=[activity])
        hamster_cli._activities(controler, 'foobar')
        out, err = capsys.readouterr()
        assert controler.activities.get_all.called
        controler.activities.get_all.assert_called_with(search_term='foobar')
        assert activity.name in out
        assert activity.category.name in out


class TestSetupLogging(object):
    """Make surr that our logging setup is executed as expected."""

    def test_setup_logging(self, controler, client_config, lib_config):
        """Test that library and client logger have log level set according to config."""
        hamster_cli._setup_logging(controler)
        assert controler.lib_logger.level == (
            controler.client_config['log_level'])
        assert controler.client_logger.level == (
            controler.client_config['log_level'])

    def test_setup_logging_log_console_true(self, controler):
        """Make sure that if console loggin is on lib and client logger have a streamhandler."""
        controler.client_config['log_console'] = True
        hamster_cli._setup_logging(controler)
        assert isinstance(controler.client_logger.handlers[0],
            logging.StreamHandler)
        assert isinstance(controler.lib_logger.handlers[0],
            logging.StreamHandler)
        assert controler.client_logger.handlers[0].formatter

    def test_setup_logging_no_logging(self, controler):
        """Make sure that if no logging enabled, our loggers don't have any handlers."""
        hamster_cli._setup_logging(controler)
        assert controler.lib_logger.handlers == []
        assert controler.client_logger.handlers == []

    def test_setup_logging_log_file_true(self, controler, appdirs):
        """Make sure that if we enable a logfile_path, both loggers recieve a ``FileHandler``."""
        controler.client_config['logfile_path'] = os.path.join(appdirs.user_log_dir, 'foobar.log')
        hamster_cli._setup_logging(controler)
        assert isinstance(controler.lib_logger.handlers[0],
            logging.FileHandler)
        assert isinstance(controler.client_logger.handlers[0],
            logging.FileHandler)


class TestGetConfig(object):
    """Make sure that turning a config instance into proper config dictionaries works."""

    @pytest.mark.parametrize('log_level', ['debug'])
    def test_log_levels_valid(self, log_level, config_instance):
        """Make sure that *string loglevels* translate to their respective integers properly."""
        backend, client = hamster_cli._get_config(
            config_instance(log_level=log_level))
        assert client['log_level'] == 10

    @pytest.mark.parametrize('log_level', ['foobar'])
    def test_log_levels_invalid(self, log_level, config_instance):
        """Test that invalid *string loglevels* raise ``ValueError``."""
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(
                config_instance(log_level=log_level))

    @pytest.mark.parametrize('day_start', ['05:00:00'])
    def test_daystart_valid(self, config_instance, day_start):
        """Test that ``day_start`` string translate to proper ``datetime.time`` instances."""
        backend, client = hamster_cli._get_config(config_instance(
            daystart=day_start))
        assert backend['day_start'] == datetime.datetime.strptime(
            '05:00:00', '%H:%M:%S').time()

    @pytest.mark.parametrize('day_start', ['foobar'])
    def test_daystart_invalid(self, config_instance, day_start):
        """Test that invalid ``day_start`` strings raises ``ValueError``."""
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(
                config_instance(daystart=day_start))

    def test_invalid_store(self, config_instance):
        """Make sure that encountering an unsupportet store will raise an exception."""
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(config_instance(store='foobar'))

    def test_non_sqlite(self, config_instance):
        """Make sure that passing a store other than 'sqlalchemy' raises exception."""
        config_instance = config_instance(db_engine='postgres')
        backend, client = hamster_cli._get_config(config_instance)
        assert backend['db_host'] == config_instance.get('Backend', 'db_host')
        assert backend['db_port'] == config_instance.get('Backend', 'db_port')
        assert backend['db_name'] == config_instance.get('Backend', 'db_name')
        assert backend['db_user'] == config_instance.get('Backend', 'db_user')
        assert backend['db_password'] == config_instance.get('Backend', 'db_password')


class TestGetConfigInstance(object):
    def test_no_file_present(self, appdirs, mocker):
        """Make sure a new vanilla config is written if no config is found."""
        mocker.patch('hamster_cli.hamster_cli._write_config_file')
        hamster_cli._get_config_instance()
        assert hamster_cli._write_config_file.called

    def test_file_present(self, config_instance, config_file, mocker):
        """Make sure we try parsing a found config file."""
        result = hamster_cli._get_config_instance()
        assert result.get('Backend', 'store') == config_instance().get('Backend', 'store')

    def test_get_config_path(self, appdirs, mocker):
        """Make sure the config target path is constructed to our expectations."""
        mocker.patch('hamster_cli.hamster_cli._write_config_file')
        hamster_cli._get_config_instance()
        expectation = os.path.join(appdirs.user_config_dir, 'hamster_cli.conf')
        assert hamster_cli._write_config_file.called_with(expectation)


class TestGenerateTable(object):
    def test_generate_table(self, fact):
        """Make sure the table contains all expected fact data."""
        table, header = hamster_cli._generate_facts_table([fact])
        assert table[0].start == fact.start.strftime('%Y-%m-%d %H:%M')
        assert table[0].activity == fact.activity.name

    def test_header(self):
        """Make sure the tables header matches our expectation."""
        table, header = hamster_cli._generate_facts_table([])
        assert len(header) == 6


class TestWriteConfigFile(object):
    def test_file_is_written(self, filepath):
        """Make sure the file is written. Content is not checked, this is ConfigParsers job."""
        hamster_cli._write_config_file(filepath)
        assert os.path.lexists(filepath)

    def test_return_config_instance(self, filepath):
        """Make sure we return a ``SafeConfigParser`` instance."""
        result = hamster_cli._write_config_file(filepath)
        assert isinstance(result, SafeConfigParser)

    def test_non_existing_path(self, tmpdir, filename):
        """Make sure that the path-parents are created ifnot present."""
        filepath = os.path.join(tmpdir.strpath, 'foobar')
        assert os.path.lexists(filepath) is False
        hamster_cli._write_config_file(filepath)
        assert os.path.lexists(filepath)


class TestHamsterAppDirs(object):
    """Make sure that our custom AppDirs works as intended."""

    def test_user_data_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_data_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.user_data_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_user_data_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_data_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.user_data_dir) is create

    def test_site_data_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.site_data_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.site_data_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_site_data_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.site_data_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.site_data_dir) is create

    def test_user_config_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_config_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.user_config_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_user_config_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_config_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.user_config_dir) is create

    def test_site_config_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.site_config_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.site_config_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_site_config_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.site_config_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.site_config_dir) is create

    def test_user_cache_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_cache_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.user_cache_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_user_cache_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_cache_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.user_cache_dir) is create

    def test_user_log_dir_returns_directoy(self, tmpdir, mocker):
        """Make sure method returns directory."""
        path = tmpdir.strpath
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_log_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        assert appdir.user_log_dir == path

    @pytest.mark.parametrize('create', [True, False])
    def test_user_log_dir_creates_file(self, tmpdir, mocker, create, faker):
        """Make sure that path creation depends on ``create`` attribute."""
        path = os.path.join(tmpdir.strpath, '{}/'.format(faker.word()))
        mocker.patch('hamster_cli.hamster_cli.appdirs.user_log_dir', return_value=path)
        appdir = hamster_cli.HamsterAppDirs('hamster_cli')
        appdir.create = create
        assert os.path.exists(appdir.user_log_dir) is create


class TestShowGreeting(object):
    """Make shure our greeting function behaves as expected."""

    def test_shows_welcome(self, capsys):
        """Make sure we welcome our users properly."""
        hamster_cli._show_greeting()
        out, err = capsys.readouterr()
        assert "Welcome to 'hamster_cli'" in out

    def test_shows_copyright(self, capsys):
        """Make sure we show basic copyright information."""
        hamster_cli._show_greeting()
        out, err = capsys.readouterr()
        assert "Copyright" in out

    def test_shows_license(self, capsys):
        """Make sure we display a brief reference to the license."""
        hamster_cli._show_greeting()
        out, err = capsys.readouterr()
        assert "GPL3" in out
        assert "'license' command" in out
