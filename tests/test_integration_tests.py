from __future__ import unicode_literals


class TestBasicRun(object):
    def test_basic_run(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner()
        assert result.exit_code == 0


class TestSearch(object):
    def test_search(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['search', 'foobar'])
        assert result.exit_code == 0


class TestList(object):
    def test_list(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['list'])
        assert result.exit_code == 0


class TestStart(object):
    def test_start(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['start', 'coding', '', ''])
        assert result.exit_code == 0


class TestStop(object):
    def test_stop(self, runner):
        """
        Make sure that invoking the command passes without exception.

        As we don't have a ``ongoing fact`` by default, we expect an expectation to be raised.
        """
        result = runner(['stop'])
        assert result.exit_code == 1


class TestCancel(object):
    def test_cancel(self, runner):
        """
        Make sure that invoking the command passes without exception.

        As we don't have a ``ongoing fact`` by default, we expect an expectation to be raised.
        """
        result = runner(['cancel'])
        assert result.exit_code == 1


class TestCurrent(object):
    def test_current(self, runner):
        """
        Make sure that invoking the command passes without exception.

        As we don't have a ``ongoing fact`` by default, we expect an expectation to be raised.
        """
        result = runner(['current'])
        assert result.exit_code == 1


class TestExport(object):
    def test_export(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['export'])
        assert result.exit_code == 0


class TestCategories(object):
    def test_categories(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['categories'])
        assert 'Error' not in result.output
        assert result.exit_code == 0


class TestActivities(object):
    def test_activities(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['activities'])
        assert 'Error' not in result.output
        assert result.exit_code == 0


class TestLicense(object):
    """Make sure command works as expected."""

    def test_license(self, runner):
        """Make sure command launches without exception."""
        result = runner(['license'])
        assert result.exit_code == 0


class TestDetails(object):
    """Make sure command works as expected."""

    def test_details(self, runner):
        """Make sure command launches without exception."""
        result = runner(['details'])
        assert result.exit_code == 0
