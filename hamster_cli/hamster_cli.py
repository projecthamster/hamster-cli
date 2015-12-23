import click
import sys
import pickle as pickle
import datetime
import os
import logging
from gettext import gettext as _
import warnings
from tabulate import tabulate
from collections import namedtuple

from hamsterlib import HamsterControl, Category, Activity, Fact
from hamsterlib import helpers


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
"""

store_config = {
    'unsorted_localized': "Unsorted",
    'store': 'sqlalchemy',
    'daystart': datetime.time(hour=0, minute=0, second=0),
    'dayend': datetime.time(hour=23, minute=59, second=59),
    'db-path': 'postgres://hamsterlib:foobar@localhost/hamsterlib',
}

client_config = {
    'tmp_dir': '.',
    'tmp_filename': 'tmp_fact.pickle',
    'log_console': True,
    'log_file': True,
    'log_filename': 'hamster_cli.log',
    'log_level': logging.DEBUG,
}

class Controler(HamsterControl):
    def __init__(self):
        super(Controler, self).__init__(store_config)
        self.client_config = client_config
        self.dbus = False

pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group()
@pass_controler
def run(controler):
    """General context provider. Is triggered on all command calls."""
    _setup_logging(controler)


@run.command()
@click.argument('time_info', default='')
@pass_controler
def list(controler, time_info):
    """List facts within a date range."""

    def generate_table(facts):
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

    if not time_info:
        start, end = (None, None)
    else:
        start, end = helpers.complete_timeframe(
            helpers.parse_time_info(time_info))


    results = controler.facts.get_all(start=start, end=end)
    table, headers = generate_table(results)
    click.echo(tabulate(table, headers=headers))
    return results


@run.command()
@click.argument('raw_fact')
@pass_controler
def start(controler, raw_fact):
    """Start or add a fact."""

    # Handle empty strings.
    if not raw_fact:
        sys.exit(_("Please provide a non-empty activity name."))

    fact = controler.parse_raw_fact(raw_fact)
    fact.start = datetime.datetime.now()
    controler.client_logger.debug(_(
        "New fact instance created: {fact}".format(fact=fact)
    ))
    if not fact.end:
        # We seem to want to start a new tmp fact
        tmp_fact = _load_tmp_fact()
        if tmp_fact:
            click.echo(_(
                "There already seems to be an ongoing Fact present. As there"
                " can be only one at a time, please use 'stop' or 'camcel' to"
                " close this existing one before starting a new one."
            ))
            controler.client_logger.info(_(
                "Trying to start with ongoing fact already present."
            ))
        else:
            result = _create_tmp_fact(fact)
            controler.client_logger.debug(_("New temporary fact started."))
    else:
        # We seem to add a complete fact
        controler.client_logger.debug(_(
            "Adding a new fact: {fact}".format(fact=fact)
        ))
        controler.facts.save(fac)
        controler.client_logger.info(_("Fact saved to db."))


@run.command()
@pass_controler
def stop(controler):
    """Stop tracking current activity."""
    fact = _load_tmp_fact()
    if fact:
        fact.end = datetime.datetime.now()
        fact = controler.facts.save(fact)
        result = _remove_tmp_fact()
        controler.client_logger.debug(_("Temporary fact stoped."))
    else:
        controler.client_logger.info(_(
            "Trying to stop a non existing ongoing fact."
        ))
        click.echo(_("Unable to continue temporary fact. Are you sure there"
                     " is one? Try running *current*."))
        result = False
    return result


@run.command()
@pass_controler
def cancel(controler):
    """Cancel tracking current temporary fact."""
    tmp_fact = _load_tmp_fact()
    if tmp_fact:
        result = _remove_tmp_fact()
        message = _("Tracking of {fact} canceled.".format(fact=tmp_fact))
        click.echo(message)
        controler.client_logger.debug(message)
    else:
        message = _("Nothing tracked right now. Not doing anything.")
        click.echo(message)
        controler.client_logger.info(message)



@run.command()
@pass_controler
def export(controler):
    """
    Export facts within the given timeframe to specified format.

    Args:
        start_time (str): Start time of timeframe.
        end_time (str): End time of timeframe.
        format (str): Output format [html|tsv|ical|xml]
"""
    raise NotImplementedError



@run.command()
@pass_controler
def categories(controler):
    """"
    List all existing categories.

    Propabbly better as a sub command to list?
    """
    result = controler.categories.get_all()
    for category in result:
        click.echo(category.name)
    return result


@run.command()
@pass_controler
def current(controler):
    """Display current tmp fact."""
    tmp_fact = _load_tmp_fact()
    if tmp_fact:
        click.echo(tmp_fact)
    else:
        click.echo(_("There seems no be no activity beeing traccked right now."
                     " maybe you want to *start* tracking one right now?"
                     ))
    return tmp_fact


@run.command()
@pass_controler
def search(controler):
    """
    List facts matching parameters.

    Note:
        Old syntax: ``search [terms] [start-time] [end-time]``

    Args:
        term (str): Search term to match.
        start_time (str): Start time for timeframe(see time formats).
        end_time (str): End time for timeframe (see time formats).

    Returns:
        list: List of Fact instance matching parameters.
    """

    raise NotImplementedError


@run.command()
@click.argument('search_term', default='')
@pass_controler
def activities(controler, search_term):
    """List all activity names."""
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
    return result

def overview():
    """Show overview window."""
    result = _launch_window('overvivew')


def statistics():
    """Show statistics window."""
    result = _launch_window('statistics')


def about():
    """Show about window."""
    result = _launch_window('about')


# Helper functions
def _setup_logging(controler):
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s %(funcName)s:  %(message)s')
    formatter2 = logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s %(funcName)s:  %(message)s')

    lib_logger = controler.lib_logger
    client_logger = logging.getLogger(__name__)
    client_logger.setLevel(client_config['log_level'])
    lib_logger.setLevel(client_config['log_level'])
    controler.client_logger = client_logger


    if client_config['log_console']:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        lib_logger.addHandler(console_handler)
        client_logger.addHandler(console_handler)

    if client_config['log_file']:
        filename = client_config['log_filename']
        file_handler = logging.FileHandler(filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        lib_logger.addHandler(file_handler)
        client_logger.addHandler(file_handler)

def _create_tmp_fact(fact):
    """Create a temporary Fact."""
    with open(_get_tmp_fact_path(), 'wb') as fobj:
        pickle.dump(fact, fobj)
    return fact

def _load_tmp_fact():
    try:
        with open(_get_tmp_fact_path(), 'rb') as fobj:
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

def _remove_tmp_fact():
    return os.remove(_get_tmp_fact_path())


def _get_tmp_fact_path():
    return os.path.join(
        client_config['tmp_dir'], client_config['tmp_filename']
    )



def _launch_window(window_type):
    raise NotImplementedError
