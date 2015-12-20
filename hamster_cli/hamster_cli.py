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

pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group()
@pass_controler
def run(controler):
    __setup_logging(controler.logger)

@run.command()
@pass_controler
def list(controler):
    click.echo(controler.facts.get_all())


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
        tmp_fact = __load_tmp_fact()
        if tmp_fact:
            click.echo(_(
                "There already seems to be an ongoing Fact present. As there"
                " can be only one at a time, please use 'stop' or 'camcel' to"
                " close this existing one before starting a new one."
            ))
            controler.logger.debug(_("Trying to start with tmp_fact already present."))
        else:
            fact.start = datetime.datetime.now()
            result = __create_tmp_fact(raw_fact)
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
    fact = __load_tmp_fact()
    fact.end = datetime.datetime.now()
    result = controler.facts.save(fact)
    logg


@run.command()
@pass_controler
def export(controler):
    raise NotImplemented


@run.command()
@pass_controler
def search(controler):
    raise NotImplemented


@run.command()
@pass_controler
def activities(controler):
    raise NotImplemented


@run.command()
@pass_controler
def categories(controler):
    """"
    List all existing categories.

    Propabbly better as a sub command to list?
    """
    click.echo(controler.categories.get_all())





# Not unreasonable convinience methods
# * get all categories
# * get all activities (by category?)





# Dubious commands
# current()
# toggle()
# track()

def __setup_logging(logger):
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

def __create_tmp_fact(fact):
    """Create a temporary Fact."""
    filepath = os.path.join(client_config['tmp_dir'], client_config['tmp_filename'])
    with open(filepath, 'wb') as fobj:
        pickle.dump(fact, fobj)
    return fact


def __load_tmp_fact():
    filepath = os.path.join(client_config['tmp_dir'], client_config['tmp_filename'])
    with open(filepath, 'rb') as fobj:
        return pickle.load(fobj)








