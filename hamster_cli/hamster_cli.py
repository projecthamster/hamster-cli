import click
import pickle as pickle
import datetime
import os
import logging
from gettext import gettext as _
import warnings

from hamsterlib import HamsterControl, Category, Activity, Fact


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
}

client_config = {
    'tmp_dir': '.',
    'tmp_filename': 'tmp_fact.pickle',
    'log_console': True,
    'log_file': True,
    'log_filename': 'hamster_cli.log',
    'log_console_level': logging.DEBUG,
    'log_file_level': logging.DEBUG,
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
    _setup_logging(controler.logger)

@run.command()
@pass_controler
def list(controler):
    """
    List facts within a date range.

    Note:
        Old syntax: ``list [start-time] [end-time]``
    """
    result = controler.facts.get_all()
    click.echo(result)
    return result


@run.command()
@click.argument('raw_fact', default='')
@pass_controler
def start(controler, raw_fact):
    """
    Actually serves two purposes.
    (1) Add a complete Fact to the db.
    (2) Start an 'ongoing fact' (possibly backdating start tme.

    Should take the raw_fact exluding time info as a parameter.
    """
    # [FIXME]
    # This should be two different commands!

    fact = controler.parse_raw_fact(raw_fact)
    if not fact.end:
        # We seem to want to start a new tmp fact
        tmp_fact = _load_tmp_fact()
        if tmp_fact:
            click.echo(_(
                "There already seems to be an ongoing Fact present. As there"
                " can be only one at a time, please use 'stop' or 'camcel' to"
                " close this existing one before starting a new one."
            ))
            controler.logger.debug(_("Trying to start with tmp_fact already present."))
        else:
            fact.start = datetime.datetime.now()
            result = _create_tmp_fact(fact)
            controler.logger.debug(_("New temporary fact started."))
    else:
        # We seem to add a complete fact
        controler.facts.save(fac)
        controler.logger.info(_("Fact saved to db."))


@run.command()
@pass_controler
def stop(controler):
    """
    Stop tracking current activity
    """
    fact = _load_tmp_fact()
    if fact:
        fact.end = datetime.datetime.now()
        fact = controler.facts.save(fact)
        result = _remove_tmp_fact()
        controler.logger.info(_("Temporary fact stoped."))
    else:
        click.echo(_("Unable to continue temporary fact. Are you sure there"
                     " is one? Try running *current*."))
        result = False
    return result


@run.command()
@pass_controler
def cancel(controler):
    """Cancel tracking current temporary fact."""
    raise NotImplementedError

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
def list_categories(controler):
    """"
    List all existing categories.

    Propabbly better as a sub command to list?
    """
    result = controler.categories.get_all()
    click.echo(result)
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
@pass_controler
def list_activities(controler):
    """
    List all activity names.

    Note:
        One per line.
        It is unclear if the original talks about facts or activities here.
    """
    raise NotImplementedError

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
def _setup_logging(logger):
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:  %(message)s')

    if client_config['log_console']:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(client_config['log_console_level'])
        logger.addHandler(console_handler)

    if client_config['log_file']:
        filename = client_config['log_filename']
        file_handler = logging.FileHandler(filename, encoding='utf-8')
        file_handler.setLevel(client_config['log_file_level'])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

def _create_tmp_fact(fact):
    """Create a temporary Fact."""
    filepath = os.path.join(client_config['tmp_dir'], client_config['tmp_filename'])
    with open(filepath, 'wb') as fobj:
        pickle.dump(fact, fobj)
    return fact

def _load_tmp_fact():
    filepath = os.path.join(client_config['tmp_dir'], client_config['tmp_filename'])
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

def _remove_tmp_fact():
    filepath = os.path.join(client_config['tmp_dir'], client_config['tmp_filename'])
    return os.remove(filepath)



def _launch_window(window_type):
    raise NotImplementedError
