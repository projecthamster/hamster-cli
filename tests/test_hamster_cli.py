# -*- coding: utf-8 -*-

import pytest
import logging
from factory import Faker
import os
import datetime
from hamster_cli import hamster_cli
from freezegun import freeze_time
from hamsterlib import Fact


class TestSearch(object):
    @pytest.mark.parametrize(('search_term', 'time_range', 'expectation'), [
        ('', '', {
            'search_term': '',
            'start': None,
            'end': None,
        }),
        ('', '2015-12-12 18:00 2015-12-12 19:30', {
            'search_term': '',
            'start': datetime.datetime(2015, 12, 12, 18, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 19, 30, 0)
        }),
        ('', '2015-12-12 18:00', {
            'search_term': '',
            'start': datetime.datetime(2015, 12, 12, 18, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 23, 59, 59)
        }),
        ('', '2015-12-12', {
            'search_term': '',
            'start': datetime.datetime(2015, 12, 12, 0, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 23, 59, 59)
        }),
        ('', '13:00', {
            'search_term': '',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 23, 59, 59),
        }),
    ])
    @freeze_time('2015-12-12 18:00')
    def test_search(self, controler, mocker, fact, search_term, time_range, expectation):
        controler.facts.get_all = mocker.MagicMock(return_value=[fact])
        result = hamster_cli._search(controler, search_term, time_range)
        controler.facts.get_all.assert_called_with(**expectation)


class TestStart(object):
    @pytest.mark.parametrize(('raw_fact', 'start', 'end', 'expectation'), [
        ('foo@bar',  '2015-12-12 13:00', '2015-12-12 16:30', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': datetime.datetime(2015, 12, 12, 16, 30, 0),
        }),
        ('10:00-18:00 foo@bar',  '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': datetime.datetime(2015, 12, 25, 18, 00, 0),
        }),
    ])
    @freeze_time('2015-12-25 18:00')
    def test_start_add_new_fact(self, controler_with_logging, mocker, raw_fact, start, end, expectation):
        """
        Test that inpul validation and assignment of start/endtime works
        is done as expected.
        We are not to test the actual functionality here!
        """
        controler = controler_with_logging
        mocker.patch('hamster_cli.hamster_cli._add_fact')
        result = hamster_cli._start(controler, raw_fact, start, end)
        assert hamster_cli._add_fact.called
        args, kwargs = hamster_cli._add_fact.call_args
        controler, fact = args
        assert fact.start == expectation['start']
        assert fact.end == expectation['end']
        assert fact.activity.name == expectation['activity']
        assert fact.category.name == expectation['category']


    @pytest.mark.parametrize(('raw_fact', 'start', 'end', 'expectation'), [
        ('foo@bar',  '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': None,
        }),
        ('11:00 foo@bar',  '2015-12-12 13:00', '', {
            'activity': 'foo',
            'category': 'bar',
            'start': datetime.datetime(2015, 12, 12, 13, 0, 0),
            'end': None,
        }),
    ])
    @freeze_time('2015-12-25 18:00')
    def test_start_tmp_fact(self, mocker, controler_with_logging, raw_fact, start, end, expectation):
        """
        Test that input validation and assignment of start/endtime works
        is done as expected.
        We are not to test the actual functionality here!
        """
        controler = controler_with_logging
        mocker.patch('hamster_cli.hamster_cli._start_tmp_fact')
        result = hamster_cli._start(controler, raw_fact, start, end)
        assert hamster_cli._start_tmp_fact.called
        args, kwargs = hamster_cli._start_tmp_fact.call_args
        controler, fact = args
        assert fact.start == expectation['start']
        assert fact.end == expectation['end']
        assert fact.activity.name == expectation['activity']
        assert fact.category.name == expectation['category']


class TestStop(object):
    def test_stop_existing_tmp_fact(self, tmp_fact, controler_with_logging, mocker):
        controler = controler_with_logging
        controler.facts.save = mocker.MagicMock()
        hamster_cli._stop(controler)
        assert controler.facts.save.called

    def test_stop_no_existing_tmp_fact(self, controler_with_logging, capsys):
        controler = controler_with_logging
        hamster_cli._stop(controler)
        out, err = capsys.readouterr()
        assert 'Unable to continue' in out


class TestCancel():
    def test_cancel_existing_tmp_fact(self, tmp_fact, controler_with_logging, mocker,
            capsys):
        controler = controler_with_logging
        mocker.patch('hamster_cli.hamster_cli._remove_tmp_fact')
        hamster_cli._cancel(controler)
        out, err = capsys.readouterr()
        assert 'canceled' in out

    def test_cancel_no_existing_tmp_fact(self, controler_with_logging, capsys):
        hamster_cli._cancel(controler_with_logging)
        out, err = capsys.readouterr()
        assert 'Nothing tracked right now' in out


class TestExport():
    pass


class TestCategories():
    def test_categories(self, controler, category, mocker, capsys):
        controler.categories.get_all = mocker.MagicMock(return_value=[category])
        hamster_cli._categories(controler)
        out, err = capsys.readouterr()
        assert category.name in out


class TestCurrent():
    def test_tmp_fact(self, controler, tmp_fact, capsys):
        hamster_cli._current(controler)
        out, err = capsys.readouterr()
        assert tmp_fact.activity.name in out

    def test_no_tmp_fact(self, controler, capsys):
        hamster_cli._current(controler)
        out, err = capsys.readouterr()
        assert 'no activity beeing tracked' in out


class TestActivities():
    def test_activities_no_category(self, controler, activity, mocker, capsys):
        activity.category = None
        controler.activities.get_all = mocker.MagicMock(return_value=[activity])
        mocker.patch('hamster_cli.hamster_cli.tabulate')
        hamster_cli.tabulate = mocker.MagicMock(
            return_value='{}, {}'.format(activity.name, None))
        hamster_cli._activities(controler, '')
        out, err = capsys.readouterr()
        assert activity.name in out
        hamster_cli.tabulate.call_args[0] == [(activity.name, None)]

    def test_activities_with_category(self, controler, activity, mocker, capsys):
        controler.activities.get_all = mocker.MagicMock(return_value=[activity])
        hamster_cli._activities(controler, '')
        out, err = capsys.readouterr()
        assert activity.name in out
        assert activity.category.name in out

    def test_activities_with_category(self, controler, activity, mocker,
            capsys):
        controler.activities.get_all = mocker.MagicMock(return_value=[activity])
        hamster_cli._activities(controler, '')
        out, err = capsys.readouterr()
        assert activity.name in out
        assert activity.category.name in out

    def test_activities_with_search_term(self, controler, activity, mocker,
            capsys):
        """Make sure the search term is passed on."""
        controler.activities.get_all = mocker.MagicMock(return_value=[activity])
        hamster_cli._activities(controler, 'foobar')
        out, err = capsys.readouterr()
        assert controler.activities.get_all.called
        controler.activities.get_all.assert_called_with(search_term='foobar')
        assert activity.name in out
        assert activity.category.name in out


class TestSetupLogging():
    def test_setup_logging(self, controler, client_config, lib_config):
        hamster_cli._setup_logging(controler)
        assert controler.lib_logger.level == controler.client_config['log_level']
        assert controler.client_logger.level == controler.client_config['log_level']

    def test_setup_logging_log_console_True(self, controler):
        controler.client_config['log_console'] = True
        hamster_cli._setup_logging(controler)
        assert isinstance(controler.client_logger.handlers[0], logging.StreamHandler)
        assert isinstance(controler.lib_logger.handlers[0], logging.StreamHandler)
        assert controler.client_logger.handlers[0].formatter

    def test_setup_logging_log_console_False(self, controler):
        hamster_cli._setup_logging(controler)
        assert controler.lib_logger.handlers == []
        assert controler.client_logger.handlers == []

    def test_setup_logging_log_file_True(self, controler):
        controler.client_config['log_file'] = True
        controler.client_config['log_filename'] = 'foobar.log'
        hamster_cli._setup_logging(controler)
        assert isinstance(controler.lib_logger.handlers[0], logging.FileHandler)
        assert isinstance(controler.client_logger.handlers[0], logging.FileHandler)

    def test_setup_logging_log_file_False(self, controler):
        hamster_cli._setup_logging(controler)
        assert controler.lib_logger.handlers == []
        assert controler.client_logger.handlers == []


class TestCreateTmpFact():
    def test_create_tmp_fact(self, fact, tmpdir):
        fobj = tmpdir.join('foo.pickle')
        result = hamster_cli._create_tmp_fact(str(fobj.realpath()), fact)
        assert os.path.isfile(str(fobj.realpath()))
        assert result is fact


class TestLoadTmpFact():
    def test_load_tmp_fact_no_file(self):
        assert hamster_cli._load_tmp_fact('foobar.pickle') is False

    def test_load_tmp_fact_no_fact_in_file(self, invalid_tmp_fact, client_config):
        with pytest.raises(TypeError):
            hamster_cli._load_tmp_fact(client_config['tmp_filename'])

    def test_load_tmp_fact(self, fact, tmp_fact, client_config):
        result = hamster_cli._load_tmp_fact(client_config['tmp_filename'])
        assert result.activity.name == fact.activity.name
        assert isinstance(result, Fact)


class TestRemoveTmpFact():
    def test_remove_tmp_fact(self, tmp_fact, client_config):
        hamster_cli._remove_tmp_fact(client_config['tmp_filename'])
        assert os.path.isfile(client_config['tmp_filename']) is False

    def test_remove_tmp_fact_no_file(self, client_config):
        with pytest.raises(OSError):
            hamster_cli._remove_tmp_fact(client_config['tmp_filename'])


class TestGetTmpFactPath(object):
    def test_get_path(self, controler, client_config):
        """Make sure that we compose the path properly."""

        # Should find a way to do this without duplicating tested code.
        result = hamster_cli._get_tmp_fact_path(client_config)
        assert result == os.path.join(client_config['cwd'],
            client_config['tmp_filename'])


class TestLaunchWindow(object):
    pass


class TestGetConfig(object):
    def test_cwd(self, config_file):
        backend, client = hamster_cli._get_config(config_file())
        assert client['cwd'] == '.'

    @pytest.mark.parametrize('log_level', ['debug'])
    def test_log_levels_valid(self, log_level, config_file):
        backend, client = hamster_cli._get_config(config_file(log_level=log_level))
        assert client['log_level'] == 10

    @pytest.mark.parametrize('log_level', ['foobar'])
    def test_log_levels_invalid(self, log_level, config_file):
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(config_file(log_level=log_level))

    @pytest.mark.parametrize('day_start', ['05:00:00'])
    def test_daystart_valid(self, config_file, day_start):
        backend, client = hamster_cli._get_config(config_file(daystart=day_start))
        assert backend['day_start'] == datetime.datetime.strptime(
            '05:00:00', '%H:%M:%S').time()

    @pytest.mark.parametrize('day_start', ['foobar'])
    def test_daystart_invalid(self, config_file, day_start):
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(config_file(daystart=day_start))

    def test_log_filename_empty(self, config_file):
        """Test that a empty filename throws an error."""
        with pytest.raises(ValueError):
            backend, client = hamster_cli._get_config(config_file(log_filename=''))
