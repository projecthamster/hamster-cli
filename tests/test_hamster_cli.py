# -*- coding: utf-8 -*-

import pytest
import datetime
from hamster_cli import hamster_cli
from freezegun import freeze_time

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
    def test_start_add_new_fact(self, controler, mocker, raw_fact, start, end, expectation):
        hamster_cli._add_fact = mocker.MagicMock(return_value=3)
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
    def test_start_tmp_fact(self, mocker, controler, raw_fact, start, end, expectation):
        hamster_cli._start_tmp_fact = mocker.MagicMock()
        result = hamster_cli._start(controler, raw_fact, start, end)
        assert hamster_cli._start_tmp_fact.called
        args, kwargs = hamster_cli._start_tmp_fact.call_args
        controler, fact = args
        assert fact.start == expectation['start']
        assert fact.end == expectation['end']
        assert fact.activity.name == expectation['activity']
        assert fact.category.name == expectation['category']



