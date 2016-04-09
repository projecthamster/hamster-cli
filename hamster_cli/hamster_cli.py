import datetime
import logging
import os
import sys
from collections import namedtuple
from gettext import gettext as _

import click
from hamsterlib import Fact, HamsterControl, helpers, reports
from tabulate import tabulate

try:
    from configparser import SafeConfigParser
except:
    from ConfigParser import SafeConfigParser


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

CONFIGFILE_PATH = './config.ini'


class Controler(HamsterControl):
    def __init__(self):
        """Instantiate controler instance and adding client_config to it."""
        lib_config, client_config = _get_config(CONFIGFILE_PATH)
        super(Controler, self).__init__(lib_config)
        self.client_config = client_config


pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group()
@pass_controler
def run(controler):
    """General context provider. Is triggered on all command calls."""
    _run()


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
    _search(search_term, time_range)


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

    results = controler.facts.get_all(search_term=search_term, start=start, end=end)

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
    _search(time_range=time_range)


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

    # Handle empty strings.
    if not raw_fact:
        raise click.ClickException(_("Please provide a non-empty activity name."))
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

    # The following is needed becauses end may be ``None``.
    if not fact.end:
        end_date = None
        end_time = None
    else:
        end_date = fact.end.date()
        end_time = fact.end.time()

    timeframe = helpers.TimeFrame(fact.start.date(), fact.start.time(),
        end_date, end_time, None)
    fact.start, fact.end = helpers.complete_timeframe(timeframe, controler.config)

    if tmp_fact:
        # Quick fix for tmp facts. that way we can use the default helper
        # function which will autocomplete the end info as well.
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

    The resulting file will be exported to ``store.lib_config['work_dir']`` and be
    named ``reports``. Its fileexension depends on the chosen format option.

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
        sys.exit(message)
    if not start:
        start = None
    if not end:
        end = None

    filename = 'report.{extension}'.format(extension=format)
    filepath = os.path.join(controler.config['work_dir'], filename)
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

    if controler.client_config['log_filename']:
        filename = controler.client_config['log_filename']
        file_handler = logging.FileHandler(filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        lib_logger.addHandler(file_handler)
        client_logger.addHandler(file_handler)


def _launch_window(window_type):
    """If ``hamster_gtk`` as well as ``dbus`` are present, launch the given window."""
    raise NotImplementedError


def _get_config(file_path):
    """
    Rertrieve config dictionaries for backend and client setup.

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
        """
        log_filename = config.get('Client', 'log_filename')
        if not log_filename:
            raise ValueError(_(
                "You specified logging to a file, but there seems to"
                " be no actual filename provided!"
            ))

        LOG_LEVELS = {
            'info': logging.INFO,
            'debug': logging.DEBUG,
            'warning': logging.WARNING,
            'error': logging.ERROR,
        }
        log_level = LOG_LEVELS.get(config.get('Client', 'log_level').lower())
        if not log_level:
            raise ValueError(_("Unrecognized log level value in config"))

        return {
            'unsorted_localized': config.get('Client', 'unsorted_localized'),
            'log_console': config.getboolean('Client', 'log_console'),
            'log_file': config.getboolean('Client', 'log_file'),
            'log_filename': config.get('Client', 'log_filename'),
            'log_level': log_level,
            'dbus': config.getboolean('Client', 'dbus'),
        }

    def get_backend_config(config):
        """
        Make sure config values are of proper type and provide basic
        sanity checks (e.g. make sure we got a filename if we want to log to
        file and such..).

        [TODO]
        Re-evaluate

        At least the validation code/sanity checks may be relevant to other
        clients as well. So mabe this qualifies for inclusion into
        hammsterlib?
        """
        try:
            day_start = datetime.datetime.strptime(config.get('Backend',
                'daystart'), '%H:%M:%S').time()
        except ValueError:
            raise ValueError(_("We encountered an error when parsing configs"
                        "'day_start' value! Aborting ..."))

        # [FIXME]
        # Thhis should live with hamsterlib instead!
        STORE_OPTIONS = ('sqlalchemy',)

        store = config.get('Backend', 'store')
        if store not in STORE_OPTIONS:
            sys.exit(_("Unrecognized store option."))

        return {
            'work_dir': config.get('Backend', 'work_dir'),
            'store': store,
            'day_start': day_start,
            'db-path': config.get('Backend', 'db_path'),
            'tmpfile_name': config.get('Backend', 'tmpfile_name'),
            'fact_min_delta': config.get('Backend', 'fact_min_delta'),
        }

    config = SafeConfigParser()
    if not config.read(file_path):
        raise IOError(_("Failed to process config file!"))

    return (get_backend_config(config), get_client_config(config))


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
