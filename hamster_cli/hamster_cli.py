import datetime
import logging
import os
import pickle as pickle
import sys
from collections import namedtuple
from gettext import gettext as _

import click
from tabulate import tabulate

from hamsterlib import Fact, HamsterControl, helpers, reports

try:
    from configparser import SafeConfigParser
except:
    from ConfigParser import SafeConfigParser



"""
The rough idea of the original CLI was that it allows to start a Fact and then,
at some later point one would stop the "current" activity.
On top of that it realy then is just some listing/exporting capabilities.

Note:
    Now, for a 'fire and forget' CLI the question is to where to store the
    "ongoing" activity if our persistend backend only wants to support complete
    facts. This is where all the mess about allowing incomplete facts to the db
    seems to take its origin...
    We stick with our doctrine of only storing complete Facts and deligating
    ongoing Facts to the client.
    In case of this CLI we just use a pickled tmp-file and be done with it.

    To promote cleanness and seperation of concens we split the actual command
    invocation and its click-integration from the logic ctriggered by that
    that command. This has the added benefit of a clear seperation of unit and
    integration tests.
"""

CONFIGFILE_PATH = './config.ini'


class Controler(HamsterControl):
    def __init__(self):
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
    """See `run` for details."""
    _setup_logging(controler)


@run.command()
@click.argument('search_term')
@click.argument('time_range', default='')
@pass_controler
def search(controler, search_term, time_range):
    _search(search_term, time_range)


def _search(controler, search_term, time_range):
    if not time_range:
        start, end = (None, None)
    else:
        start, end = helpers.complete_timeframe(
            helpers.parse_time_range(time_range),
            controler.config['day_start'],
            controler.config['day_end']
        )

    results = controler.facts.get_all(search_term=search_term, start=start,
        end=end)
    table, headers = _generate_table(results)
    click.echo(tabulate(table, headers=headers))


@run.command()
@click.argument('time_range', default='')
@pass_controler
def list(controler, time_range):
    """
    List facts within a date range.

    This is effectivly just a specical version of `search`
    """
    _search(time_range=time_range)


@run.command()
@click.argument('raw_fact')
@click.argument('start', default='')
@click.argument('end', default='')
@pass_controler
def start(controler, raw_fact, start, end):
    """Start or add a fact."""
    _start(controler, raw_fact, start, end)


def _start(controler, raw_fact, start, end):
    """See `start` for details."""

    fact = controler.parse_raw_fact(raw_fact)
    # Explicit trumps implicit!
    if start:
        fact.start = helpers.parse_time(start)
    if end:
        fact.end = helpers.parse_time(end)
    if not fact.start:
        fact.start = start or datetime.datetime.now()
    if not fact.end and end:
        fact.end = end

    controler.client_logger.debug(_(
        "New fact instance created: {fact}".format(fact=fact)
    ))
    if not fact.end:
        # We seem to want to start a new tmp fact
        fact = _start_tmp_fact(controler, fact)
    else:
        # We seem to add a complete fact
        fact = _add_fact(controler, fact)


@run.command()
@pass_controler
def stop(controler):
    """Stop tracking current activity. Saving the result."""
    _stop(controler)


def _stop(controler):
    fact = _load_tmp_fact(_get_tmp_fact_path(controler.client_config))
    if fact:
        fact.end = datetime.datetime.now()
        fact = controler.facts.save(fact)
        _remove_tmp_fact(_get_tmp_fact_path(controler.client_config))
        controler.client_logger.debug(_("Temporary fact stoped."))
        click.echo(_("Temporary fact stoped!"))
    else:
        controler.client_logger.info(_(
            "Trying to stop a non existing ongoing fact."
        ))
        click.echo(_("Unable to continue temporary fact. Are you sure there"
                     " is one? Try running *current*."))


@run.command()
@pass_controler
def cancel(controler):
    _cancel(controler)


def _cancel(controler):
    """Cancel tracking current temporary fact, discaring the result."""
    tmp_fact = _load_tmp_fact(_get_tmp_fact_path(controler.client_config))
    if tmp_fact:
        _remove_tmp_fact(_get_tmp_fact_path(controler.client_config))
        message = _("Tracking of {fact} canceled.".format(fact=tmp_fact))
        click.echo(message)
        controler.client_logger.debug(message)
    else:
        message = _("Nothing tracked right now. Not doing anything.")
        click.echo(message)
        controler.client_logger.info(message)


@run.command()
@click.argument('format', nargs=1, default='csv')
@click.argument('start', nargs=1, default='')
@click.argument('end', nargs=1, default='')
@pass_controler
def export(controler, format, start, end):
    _export(controler, format, start, end)


def _export(controler, format, start, end):
    filename = 'report.csv'
    facts = controler.facts.get_all(start=start, end=end)
    filepath = os.path.join(controler.client_config['cwd'], filename)
    if format == 'csv':
        writer = reports.TSVWriter(filepath)
    else:
        raise ValueError(_("Unrecognized export format."))
    writer.write_report(facts)


@run.command()
@pass_controler
def categories(controler):
    """"
    List all existing categories.

    Propabbly better as a sub command to list?
    """
    _categories(controler)


def _categories(controler):
    result = controler.categories.get_all()
    for category in result:
        click.echo(category.name)


@run.command()
@pass_controler
def current(controler):
    """Display current tmp fact."""

    _current(controler)


def _current(controler):
    tmp_fact = _load_tmp_fact(_get_tmp_fact_path(controler.client_config))
    if tmp_fact:
        click.echo(tmp_fact)
    else:
        click.echo(_("There seems no be no activity beeing tracked right now."
                     " maybe you want to *start* tracking one right now?"
                     ))


@run.command()
@click.argument('search_term', default='')
@pass_controler
def activities(controler, search_term):
    """List all activity names."""
    _activities(controler, search_term)


def _activities(controler, search_term):
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
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s %(funcName)s:  %(message)s')

    lib_logger = controler.lib_logger
    client_logger = logging.getLogger(__name__)
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

def _create_tmp_fact(filepath, fact):
    """Create a temporary Fact."""
    with open(filepath, 'wb') as fobj:
        pickle.dump(fact, fobj)
    return fact

def _load_tmp_fact(filepath):
    try:
        with open(filepath, 'rb') as fobj:
            fact = pickle.load(fobj)
    except IOError:
        fact = False
    else:
        if not isinstance(fact, Fact):
            raise TypeError(_(
                "Something went wrong. It seems our pickled file does not contain"
                " valid Fact instance. [Content: '{content}'; Type: {type}".format(
                    content=fact, type=type(fact))
            ))
    return fact

def _remove_tmp_fact(filepath):
    return os.remove(filepath)


def _get_tmp_fact_path(config):
    return os.path.join(
        config['cwd'], config['tmp_filename']
    )


def _launch_window(window_type):
    raise NotImplementedError

def _get_config(file_path):
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
            'cwd': config.get('Client', 'cwd'),
            'tmp_filename': config.get('Client', 'tmp_filename'),
            'log_console': config.getboolean('Client', 'log_console'),
            'log_filename': log_filename,
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
        day_end = datetime.datetime.strptime(config.get('Backend', 'dayend'),
            '%H:%M:%S').time()
        if day_end < day_start:
            sys.exit(_(
                "Your 'day_end' time seems to be before 'day_start', please"
                " please correct this."
            ))

        # [FIXME]
        # Thhis should live with hamsterlib instead!
        STORE_OPTIONS = ('sqlalchemy',)

        store = config.get('Backend', 'store')
        if store not in STORE_OPTIONS:
            sys.exit(_("Unrecognized store option."))

        return {
            'day_start': day_start,
            'day_end': day_end,
            'unsorted_localized': config.get('Backend', 'unsorted_localized'),
            'store': store,
            'db-path': config.get('Backend', 'db_path')
        }

    config = SafeConfigParser()
    if not config.read(file_path):
        raise IOError(_("Failed to process config file!"))

    return (get_backend_config(config), get_client_config(config))


def _generate_table(facts):
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
            delta='{minutes} min.'.format(minutes=(int(fact.delta.total_seconds()/60))),
        ))

    return (table, header)


def _start_tmp_fact(controler, fact):
    tmp_fact = _load_tmp_fact(_get_tmp_fact_path(controler.client_config))
    if tmp_fact:
        click.echo(_(
            "There already seems to be an ongoing Fact present. As there"
            " can be only one at a time, please use 'stop' or 'cancel' to"
            " close this existing one before starting a new one."
        ))
        controler.client_logger.info(_(
            "Trying to start with ongoing fact already present."
        ))
    else:
        result = _create_tmp_fact(_get_tmp_fact_path(
            controler.client_config),fact)
        controler.client_logger.debug(_("New temporary fact started."))


def _add_fact(controler, fact):
    controler.client_logger.debug(_(
        "Adding a new fact: {fact}".format(fact=fact)
    ))
    controler.facts.save(fact)
    controler.client_logger.info(_("Fact saved to db."))
    return True
