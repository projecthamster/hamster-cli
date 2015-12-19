import click
import datetime


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

class Controler(HamsterControl):
    def __init__(self):
        super(Controler, self).__init__(store_config)

pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group()
def run():
    pass

@run.command()
@pass_controler
def list(controler):
    click.echo(controler.facts.get_all())


@run.command()
@pass_controler
def start(controler):
    """
    Start tracking with *now* as start date.

    Should take the raw_fact exluding time info as a parameter.
    """
    raise NotImplemented


@run.command()
@pass_controler
def stop(controler):
    """
    Stop tracking current activity
    """
    raise NotImplemented


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




