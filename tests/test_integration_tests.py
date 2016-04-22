from __future__ import unicode_literals

from hamster_cli import __appname__, __version__


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


class TestOverview(object):
    def test_overview(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['overview'])
        assert 'Error' not in result.output
        assert result.exit_code == -1


class TestStatistics(object):
    def test_statistics(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['statistics'])
        assert 'Error' not in result.output
        assert result.exit_code == -1


class TestAbout(object):
    def test_about(self, runner):
        """Make sure that invoking the command passes without exception."""
        result = runner(['about'])
        assert 'Error' not in result.output
        assert result.exit_code == -1


class TestLicense(object):
    """Make sure command works as expected."""

    def test_license(self, runner):
        """Make sure command launches without exception."""
        result = runner(['license'])
        assert result.exit_code == 0

    def test_license_is_shown(self, runner):
        """Make sure the license text is actually displayed."""
        result = runner(['license'])
        assert "'hamster_cli' is free software" in result.output
        assert "GNU General Public License" in result.output
        assert "version 3" in result.output


class TestDetails(object):
    """Make sure command works as expected."""

    def test_details(self, runner):
        """Make sure command launches without exception."""
        result = runner(['details'])
        assert result.exit_code == 0

    def test_details_general_data_is_shown(self, runner):
        """Make sure user recieves the desired output."""
        result = runner(['details'])
        assert __appname__ in result.output
        assert __version__ in result.output
        assert 'Configuration' in result.output
        assert 'Logfile' in result.output
        assert 'Reports' in result.output

    def test_details_sqlite(self, runner, appdirs, mocker, get_config_file):
        """Make sure database details for sqlite are shown properly."""
        mocker.patch('hamsterlib.lib.HamsterControl._get_store')
        engine, path = 'sqlite', appdirs.user_data_dir
        get_config_file(db_engine=engine, db_path=path)
        result = runner(['details'])
        assert engine in result.output
        assert path in result. output

    def test_details_non_sqlite(self, runner, get_config_file, db_port, db_host, db_name,
            db_user, db_password, mocker):
        """
        Make sure database details for non-sqlite are shown properly.

        We need to mock the backend Controler because it would try to setup a
        database connection right away otherwise.
        """
        mocker.patch('hamsterlib.lib.HamsterControl._get_store')
        get_config_file(db_engine='postgres', db_name=db_name, db_host=db_host,
            db_user=db_user, db_password=db_password, db_port=db_port)
        result = runner(['details'])
        assert 'postgres' in result.output
        assert db_host in result.output
        assert db_name in result.output
        assert db_user in result.output
        assert db_password not in result.output
        if db_port:
            assert db_port in result.output
