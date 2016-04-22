# -*- coding: utf-8 -*-

# This file is part of 'hamster_cli'.
#
# 'hamster_cli' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# 'hamster_cli' is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 'hamster_cli'.  If not, see <http://www.gnu.org/licenses/>.

"""
The rough idea of the original CLI was that it allows to start a Fact and then,
at some later point one would stop the "current" activity.
On top of that it realy then is just some listing/exporting capabilities.

The main tasks of this CLI are twofold:
    1. Provide a structured and solid config to be handed over to the backend.
    2. Provide a clean interface that includes some basic input validation before
        calling upon ``hamsterlib`` to do the heavy lifting.

  To promote cleanness and seperation of concens we split the actual command
    invocation and its click-integration from the logic ctriggered by that
    that command. This has the added benefit of a clear seperation of unit and
    integration tests.

    * For information about unicode handling, see:
        http://click.pocoo.org/6/python3/#python3-surrogates This should be alright for
        our usecase, as any properly user environment should have its unicode locale declared.
        And if not, its acceptable to bully the user to do so.

    * Click commands deal only with strings. So quite often, the first thing our
        custom command-functions will do is provide some basic type conversion and
        error checking. before calling the corresponding lib method.
    * Whilst the backend usualy either returns results or Errors, the client should
        always try to handle those errors which are predictable and turn them into user
        relevant command line output. Only actual errors that are not part of the expected
        user interaction shall get through as exceptions.
"""
from __future__ import absolute_import, unicode_literals

import datetime
import logging
import os
from collections import namedtuple
from gettext import gettext as _

import appdirs
import click
import hamsterlib
# Once we drop py2 support, we can use the builtin again but unicode support
# under python 2 is practicly non existing and manual encoding is not easily
# possible.
from backports.configparser import SafeConfigParser
from hamsterlib import Fact, HamsterControl, helpers, reports
from tabulate import tabulate


class HamsterAppDirs(appdirs.AppDirs):
    """Custom class that ensure appdirs exist."""
    def __init__(self, *args, **kwargs):
        """Add create flag value to instance."""
        super(HamsterAppDirs, self).__init__(*args, **kwargs)
        self.create = True

    @property
    def user_data_dir(self):
        """Return ``user_data_dir``."""
        directory = appdirs.user_data_dir(self.appname, self.appauthor,
                             version=self.version, roaming=self.roaming)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    @property
    def site_data_dir(self):
        """Return ``site_data_dir``."""
        directory = appdirs.site_data_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    @property
    def user_config_dir(self):
        """Return ``user_config_dir``."""
        directory = appdirs.user_config_dir(self.appname, self.appauthor,
                               version=self.version, roaming=self.roaming)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    @property
    def site_config_dir(self):
        """Return ``site_config_dir``."""
        directory = appdirs.site_config_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    @property
    def user_cache_dir(self):
        """Return ``user_cache_dir``."""
        directory = appdirs.user_cache_dir(self.appname, self.appauthor,
                              version=self.version)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    @property
    def user_log_dir(self):
        """Return ``user_log_dir``."""
        directory = appdirs.user_log_dir(self.appname, self.appauthor,
                            version=self.version)
        if self.create:
            self._ensure_directory_exists(directory)
        return directory

    def _ensure_directory_exists(self, directory):
        """Ensure that the passed path exists."""
        if not os.path.lexists(directory):
            os.makedirs(directory)
        return directory


AppDirs = HamsterAppDirs('hamster_cli')


class Controler(HamsterControl):
    def __init__(self):
        """Instantiate controler instance and adding client_config to it."""
        lib_config, client_config = _get_config(_get_config_instance())
        super(Controler, self).__init__(lib_config)
        self.client_config = client_config


pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group()
@pass_controler
def run(controler):
    """General context provider. Is triggered on all command calls."""
    _run(controler)


def _run(controler):
    """Make sure that loggers are setup properly"""
    _setup_logging(controler)


@run.command()
@click.argument('search_term')
@click.argument('time_range', default='')
@pass_controler
def search(controler, search_term, time_range):
    """
    Search facts maching given timerange and search term. Both are optional.

    Matching facts will be printed in a tabular representation.

    Args:
        search_term: Term that need to be matched by the fact in order to be considered a hit.
        time_range (optional): Only fact within this timerange will be considered.

    """
    _search(controler, search_term, time_range)


def _search(controler, search_term, time_range):
    """
    Refer to ``search`` for general information.

    Make sure that arguments are converted into apropiate types before passing
    them on to the backend.

    We leave it to the backend to first parse the timeinfo and then complete any
    missing data based on the passed config settings.
    """

    if not time_range:
        start, end = (None, None)
    else:
        start, end = helpers.complete_timeframe(helpers.parse_time_range(time_range),
            controler.config)

    results = controler.facts.get_all(filter_term=search_term, start=start, end=end)

    table, headers = _generate_facts_table(results)
    click.echo(tabulate(table, headers=headers))


@run.command()
@click.argument('time_range', default='')
@pass_controler
def list(controler, time_range):
    """
    List facts within a date range.

    Matching facts will be printed in a tabular representation.

    Args:
        time_range (optional): Only fact within this timerange will be considered.

    Note:
        * This is effectivly just a specical version of `search`
    """
    _search(controler, search_term='', time_range=time_range)


@run.command()
@click.argument('raw_fact')
@click.argument('start', default='')
@click.argument('end', default='')
@pass_controler
def start(controler, raw_fact, start, end):
    """Start or add a fact.

    Args:
        raw_fact: ``raw_fact`` containing information about the Fact to be started. As an absolute
            minimum this must be a string representing the 'activityname'.
        start (optional): When does the fact start?
        end (optional): When does the fact end?
    """
    # [FIXME]
    # The original semantics do not work anymore. As we make a clear difference
    # between *adding* a (complete) fact and *starting* a (ongoing) fact.
    # This needs to be reflected in this command.
    _start(controler, raw_fact, start, end)


def _start(controler, raw_fact, start, end):
    """See `start` for details.

    Note:
        * Whilst it is possible to pass timeinformation as part of the ``raw_fact`` as
            well as dedicated ``start`` and ``end`` arguments only the latter will be represented
            in the resulting fact in such a case.
    """

    fact = Fact.create_from_raw_fact(raw_fact)
    # Explicit trumps implicit!
    if start:
        fact.start = helpers.parse_time(start)
    if end:
        fact.end = helpers.parse_time(end)

    if not fact.end:
        # We seem to want to start a new tmp fact
        # Neither the raw fact string nor an additional optional end time have
        # been passed.
        # Until we decide wether to split this into start/add command we use the
        # presence of any 'end' information as indication of the users intend.
        tmp_fact = True
    else:
        tmp_fact = False

    # We complete the facts times in both cases as even an new 'ongoing' fact
    # may be in need of some time-completion for its start information.

    # Complete missing fields with default values.
    # legacy hamster_cli seems to have a different fallback behaviour than
    # our regular backend, in particular the way 'day_start' is handled.
    # For maximum consistency we use the backends unified ``complete_timeframe``
    # helper instead. If behaviour similar to the legacy hamster-cli is desired,
    # all that seems needed is to change ``day_start`` to '00:00'.

    # The following is needed becauses start and end may be ``None``.
    if not fact.start:
        # No time information has been passed at all.
        fact.start = datetime.datetime.now()

    else:
        # We got some time information, which may be incomplete however.
        if not fact.end:
            end_date = None
            end_time = None
        else:
            end_date = fact.end.date()
            end_time = fact.end.time()

        timeframe = helpers.TimeFrame(
            fact.start.date(), fact.start.time(), end_date, end_time, None)
        fact.start, fact.end = helpers.complete_timeframe(timeframe, controler.config)

    if tmp_fact:
        # Quick fix for tmp facts. that way we can use the default helper
        # function which will autocomplete the end info as well.
        # Because of our use of ``complete timeframe our 'ongoing fact' may have
        # recieved an ``end`` value now. In that case we reset it to ``None``.
        fact.end = None

    controler.client_logger.debug(_(
        "New fact instance created: {fact}".format(fact=fact)
    ))
    fact = controler.facts.save(fact)


@run.command()
@pass_controler
def stop(controler):
    """
    Stop tracking current fact. Saving the result.

    Provide a confirmation/failure message to the user.
    """
    _stop(controler)


def _stop(controler):
    """Stop cucrrent 'ongoing fact' and save it to the backend. See ``stop`` for details."""
    try:
        controler.facts.stop_tmp_fact()
    except ValueError:
        message = _(
            "Unable to continue temporary fact. Are you sure there is one?"
            "Try running *current*."
        )
        raise click.ClickException(message)
    else:
        controler.client_logger.info(_("Temporary fact stoped."))
        click.echo(_("Temporary fact stoped!"))


@run.command()
@pass_controler
def cancel(controler):
    """
    Cancel 'ongoing fact'. E.g stop it without storing in the backend.


    Provide a confirmation/failure message to the user.
    """
    _cancel(controler)


def _cancel(controler):
    """Cancel tracking current temporary fact, discaring the result."""
    try:
        controler.facts.cancel_tmp_fact()
    except KeyError:
        message = _("Nothing tracked right now. Not doing anything.")
        controler.client_logger.info(message)
        raise click.ClickException(message)
    else:
        message = _("Tracking canceled.")
        click.echo(message)
        controler.client_logger.debug(message)


@run.command()
@click.argument('format', nargs=1, default='csv')
@click.argument('start', nargs=1, default='')
@click.argument('end', nargs=1, default='')
@pass_controler
def export(controler, format, start, end):
    """
    Export all facts of within a given timewindow to a file of specified format.

    Args:
        format (optional): Export format. Currently supported options are: 'csv'.
            Defaults to ``csv``.
        start (optional): Start of timewindow. Defaults to ``empty string``.
        end (optional): End of timewindow. Defaults to ``empty string``.
    """
    _export(controler, format, start, end)


def _export(controler, format, start, end):
    accepted_formats = ['csv']
    # [TODO]
    # Once hamsterlib has a proper 'export' register available we should be able
    # to streamline this.
    if format not in accepted_formats:
        message = _("Unrecocgnized export format recieved")
        controler.client_logger.info(message)
        raise click.ClickException(message)
    if not start:
        start = None
    if not end:
        end = None

    filepath = controler.client_config['export_path']
    facts = controler.facts.get_all(start=start, end=end)
    if format == 'csv':
        writer = reports.TSVWriter(filepath)
        writer.write_report(facts)
        click.echo(_("Facts have been exported to: {path}".format(path=filepath)))


@run.command()
@pass_controler
def categories(controler):
    """"
    List all existing categories, ordered by name.

    Note:
        * Propabbly better as a sub command to list?
    """
    _categories(controler)


def _categories(controler):
    """For details, refer to ``categories``."""
    result = controler.categories.get_all()
    # [TODO]
    # Provide nicer looking tabulated output.
    for category in result:
        click.echo(category.name)


@run.command()
@pass_controler
def current(controler):
    """Display current tmp fact."""

    _current(controler)


def _current(controler):
    try:
        fact = controler.facts.get_tmp_fact()
    except KeyError:
        message = _(
            "There seems no be no activity beeing tracked right now."
            " maybe you want to *start* tracking one right now?"
        )
        raise click.ClickException(message)
    else:
        click.echo(fact)


@run.command()
@click.argument('search_term', default='')
@pass_controler
def activities(controler, search_term):
    """
    List all activits. Provide optional filtering by name.

    Prints all matching activities one per line.

    Args:
        search (optional): String to be matched against activity name.

    """
    _activities(controler, search_term)


def _activities(controler, search_term):
    """For details see ``activities``."""
    result = controler.activities.get_all(search_term=search_term)
    table = []
    headers = (_("Activity"), _("Category"))
    for activity in result:
        if activity.category:
            category = activity.category.name
        else:
            category = None
        table.append((activity.name, category))

    click.echo(tabulate(table, headers=headers))


@run.command()
def overview():
    """Show overview window."""
    _launch_window('overview')


@run.command()
def statistics():
    """Show statistics window."""
    _launch_window('statistics')


@run.command()
def about():
    """Show about window."""
    _launch_window('about')


@run.command()
def license():
    """Show license information"""
    license = """
        'hamster_cli' is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        'hamster_cli' is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with .  If not, see <http://www.gnu.org/licenses/>.
        """
    click.echo(license)


@run.command()
@pass_controler
def details(controler):
    """List details about the runtime environment."""
    def get_db_info():
        result = None

        def get_sqlalchemy_info():
            engine = controler.config['db_engine']
            if engine == 'sqlite':
                sqlalchemy_string = _("Using 'sqlite' with database stored under: {}".format(
                    controler.config['db_path']))
            else:
                port = controler.config.get('db_port', '')
                if port:
                    port = ':{}'.format(port)

                sqlalchemy_string = _(
                    "Using '{engine}' connecting to database {name} on {host}{port}"
                    " as user {username}.".format(
                        engine=engine, host=controler.config['db_host'], port=port,
                        username=controler.config['db_user'], name=controler.config['db_name'])
                )
            return sqlalchemy_string

        # For now we do not need to check for various store option as we allow
        # only one anyway.
        result = get_sqlalchemy_info()
        return result

    from hamster_cli import __version__, __appname__
    click.echo(_("You are running {name} version {version}.".format(
        name=__appname__, version=__version__)))
    click.echo("Configuration found under: {}.".format(_get_config_path()))
    click.echo("Logfile stored under: {}.".format(controler.client_config['logfile_path']))
    click.echo("Reports exported to: {}.".format(controler.client_config['export_path']))
    click.echo(get_db_info())


# Helper functions
def _setup_logging(controler):
    """Setup logging for the lib_logger as well as client specific logging."""
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s %(funcName)s:  %(message)s')

    lib_logger = controler.lib_logger
    client_logger = logging.getLogger('hamster_cli')
    # Clear any existing (null)Handlers
    lib_logger.handlers = []
    client_logger.handlers = []
    client_logger.setLevel(controler.client_config['log_level'])
    lib_logger.setLevel(controler.client_config['log_level'])
    controler.client_logger = client_logger

    if controler.client_config['log_console']:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        lib_logger.addHandler(console_handler)
        client_logger.addHandler(console_handler)

    if controler.client_config['logfile_path']:
        filename = controler.client_config['logfile_path']
        file_handler = logging.FileHandler(filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        lib_logger.addHandler(file_handler)
        client_logger.addHandler(file_handler)


def _launch_window(window_type):
    """If ``hamster_gtk`` as well as ``dbus`` are present, launch the given window."""
    raise NotImplementedError


def _get_config(config_instance):
    """
    Rertrieve config dictionaries for backend and client setup.

    Raises:
        ValueError: Raised if we fail to process the user supplied config information.
            Please note that there will be no log entry as at this point, logging has not
            been set up yet.

    Returns:
        tuple: ``backend_config, client_config)`` tuple, where each element is a
            dictionary storing relevant config data.
    """
    # [TODO]
    # We propably can make better use of configparsers default config optionn,
    # but for now this will do.

    def get_client_config(config):
        """
        Make sure config values are of proper type and provide basic
        sanity checks (e.g. make sure we got a filename if we want to log to
        file and such..).

        Not all key/values returned here need to be user configurable!

        It is worth noting that this is where we turn our user provided config information
        into the actual dictionaries to be consumed by our backend and client objects.
        A particular consequence is that the division of "Client/Backend" in the config
        file is purely cosmetic. Another consequence is that not all user provided config
        information has to be processed at all. We just take what we need and can safely
        ignore the rest. That way we can improve the config file layout without having to
        adjust our code all the time. It also means our main code does not have to deal with
        turning ``path`` plus ``name`` into a full location and such.
        """

        def get_logfile_path():
            log_dir = AppDirs.user_log_dir
            return os.path.join(log_dir, config.get('Client', 'log_filename'))

        def get_log_level():
            LOG_LEVELS = {
                'info': logging.INFO,
                'debug': logging.DEBUG,
                'warning': logging.WARNING,
                'error': logging.ERROR,
            }
            try:
                log_level = LOG_LEVELS[config.get('Client', 'log_level').lower()]
            except KeyError:
                raise ValueError(_("Unrecognized log level value in config"))
            return log_level

        def get_log_console():
            return config.getboolean('Client', 'log_console')

        def get_export_dir():
            """Return path to save exports to. Filenextension will be added by export method."""
            return os.path.join(AppDirs.user_data_dir, 'export')

        return {
            'log_level': get_log_level(),
            'log_console': get_log_console(),
            'logfile_path': get_logfile_path(),
            'export_path': get_export_dir(),
        }

    def get_backend_config(config):
        """
        Return properly populated config dictionaries for consumption by our application.

        Make sure config values are of proper type and provide basic
        sanity checks (e.g. make sure we got a filename if we want to log to
        file and such..).

        Setting of config values that are not actually derived from our config file but by
        inspecting our runtime environment (e.g. path information) happens here as well.

        Note:
            At least the validation code/sanity checks may be relevant to other
            clients as well. So mabe this qualifies for inclusion into
            hammsterlib?
        """

        def get_day_start():
            try:
                day_start = datetime.datetime.strptime(config.get('Backend',
                    'daystart'), '%H:%M:%S').time()
            except ValueError:
                raise ValueError(_("We encountered an error when parsing configs"
                            "'day_start' value! Aborting ..."))
            return day_start

        def get_store():
            store = config.get('Backend', 'store')
            if store not in hamsterlib.lib.REGISTERED_BACKENDS.keys():
                raise ValueError(_("Unrecognized store option."))
            return store

        def get_db_path():
            return config.get('Backend', 'db_path')

        def get_fact_min_delta():
            return config.get('Backend', 'fact_min_delta')

        def get_tmpfile_path():
            """Return path to file used to store *ongoing fact*"""
            return os.path.join(AppDirs.user_data_dir, 'hamster_cli.fact')

        def get_db_config():
            """Provide a dict with db-specifiy key/value to be added to the backend config."""
            result = {}
            engine = config.get('Backend', 'db_engine')
            result = {'db_engine': engine}
            if engine == 'sqlite':
                result.update({'db_path': config.get('Backend', 'db_path')})
            else:
                try:
                    result.update({'db_port': config.get('Backend', 'db_port')})
                except KeyError:
                    pass

                result.update({
                    'db_host': config.get('Backend', 'db_host'),
                    'db_name': config.get('Backend', 'db_name'),
                    'db_user': config.get('Backend', 'db_user'),
                    'db_password': config.get('Backend', 'db_password'),
                })
            return result

        backend_config = {
            'store': get_store(),
            'day_start': get_day_start(),
            'fact_min_delta': get_fact_min_delta(),
            'tmpfile_path': get_tmpfile_path(),
        }
        backend_config.update(get_db_config())
        return backend_config

    return (get_backend_config(config_instance), get_client_config(config_instance))


def _get_config_instance():
    """
    Return a SafeConfigParser instance.

    If we can not find a config file under its expected location, we trigger creation
    of a new default file and return its instance.

    Returns:
        SafeConfigParser: Either the config loaded from file or an instance representing
            the content of our newly creating default config.
    """
    config = SafeConfigParser()
    configfile_path = _get_config_path()
    if not config.read(configfile_path):
        click.echo(_("No valid config file found. Trying to create a new default config"
                     " at: '{}'.".format(configfile_path)))
        config = _write_config_file(configfile_path)
        click.echo(_("A new default config file has been successfully created."))
    return config


def _get_config_path():
    """Show general information upon client launch."""
    config_dir = AppDirs.user_config_dir
    config_filename = 'hamster_cli.conf'
    return os.path.join(config_dir, config_filename)


def _write_config_file(file_path):
    """
    Write a default config file to the specified location.

    Returns:
        SafeConfigParser: Instace written to file.
    """
    # [FIXME]
    # This may be usefull to turn into a proper command, so users can restore to
    # factory settings easily.

    def get_db_path():
        return os.path.join(str(AppDirs.user_data_dir), 'hamster_cli.sqlite')

    def get_tmp_file_path():
        return os.path.join(str(AppDirs.user_data_dir), 'hamster_cli.fact')

    config = SafeConfigParser()

    # Backend
    config.add_section('Backend')
    config.set('Backend', 'store', 'sqlalchemy')
    config.set('Backend', 'daystart', '00:00:00')
    config.set('Backend', 'fact_min_delta', '60')
    config.set('Backend', 'db_engine', 'sqlite')
    config.set('Backend', 'db_host', '')
    config.set('Backend', 'db_port', '')
    config.set('Backend', 'db_name', '')
    config.set('Backend', 'db_path', get_db_path())
    config.set('Backend', 'db_user', '')
    config.set('Backend', 'db_password', '')

    # Client
    config.add_section('Client')
    config.set('Client', 'unsorted_localized', 'Unsorted')
    config.set('Client', 'log_level', 'debug')
    config.set('Client', 'log_console', 'False')
    config.set('Client', 'log_filename', 'hamster_cli.log')

    configfile_path = os.path.dirname(file_path)
    if not os.path.lexists(configfile_path):
        os.makedirs(configfile_path)
    with open(file_path, 'w') as fobj:
        config.write(fobj)

    return config


def _generate_facts_table(facts):
    """
    Create a nice looking table representing a set of fact instances.

    Returns a (table, header) tuple. 'table' is a list of ``TableRow``
    instances representing a single fact.
    """
    # If you want to change the order just adjust the dict.
    headers = {
        'start': _("Start"),
        'end': _("End"),
        'activity': _("Activity"),
        'category': _("Category"),
        'description': _("Description"),
        'delta': _("Duration")
    }

    columns = ('start', 'end', 'activity', 'category', 'description',
        'delta')

    header = [headers[column] for column in columns]

    TableRow = namedtuple('TableRow', columns)

    table = []
    for fact in facts:
        if fact.category:
            category = fact.category.name
        else:
            category = ''

        table.append(TableRow(
            activity=fact.activity.name,
            category=category,
            description=fact.description,
            start=fact.start.strftime('%Y-%m-%d %H:%M'),
            end=fact.end.strftime('%Y-%m-%d %H:%M'),
            # [TODO]
            # Use ``Fact.get_string_delta`` instead!
            delta='{minutes} min.'.format(minutes=(int(fact.delta.total_seconds() / 60))),
        ))

    return (table, header)


def _show_greeting():
    click.echo(_("Welcome to 'hamster_cli', your friendly time tracker for the command line."))
    click.echo("Copyright (C) 2015-2016, Eric Goller <elbenfreund@DenkenInEchtzeit.net>")
    click.echo(_(
        "'hamster_cli' is published under the terms of the GPL3, for details please use"
        "the 'license' command."
    ))
    click.echo()

if __name__ == '__main__':
    click.clear()
    _show_greeting()
    run()
