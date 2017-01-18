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

"""A time tracker for the command line. Utilizing the power of hamster-lib."""


from __future__ import absolute_import, unicode_literals

import datetime
import logging
import os
from collections import namedtuple
from gettext import gettext as _

import pyparsing as pp

import appdirs
import click
import hamster_lib
# Once we drop py2 support, we can use the builtin again but unicode support
# under python 2 is practicly non existing and manual encoding is not easily
# possible.
from backports.configparser import SafeConfigParser
from hamster_lib import Fact, HamsterControl, reports
from hamster_lib.helpers import time as time_helpers
from tabulate import tabulate

from . import help_strings

# Disable the python_2_unicode_compatible future import warning.
click.disable_unicode_literals_warning = True


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


class Controler(HamsterControl):
    """A custom controler that adds config handling on top of its regular functionality."""

    def __init__(self):
        """Instantiate controler instance and adding client_config to it."""
        lib_config, client_config = _get_config(_get_config_instance())
        super(Controler, self).__init__(lib_config)
        self.client_config = client_config


LOG_LEVELS = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'warning': logging.WARNING,
    'error': logging.ERROR,
}


AppDirs = HamsterAppDirs('hamster_cli')


pass_controler = click.make_pass_decorator(Controler, ensure=True)


@click.group(help=help_strings.RUN_HELP)
@pass_controler
def run(controler):
    """General context run right before any of the commands."""
    click.clear()
    _show_greeting()
    _run(controler)


def _run(controler):
    """Make sure that loggers are setup properly."""
    _setup_logging(controler)


@run.command(help=help_strings.SEARCH_HELP)
#@click.argument('time_range', default='')
@click.option('-s', '--start', help = 'The start time string (e.g. "2017-01-01 00:00").')
@click.option('-e', '--end', help = 'The end time string (e.g. "2017-02-01 00:00").')
@click.option('-a', '--activity', help = "The search string applied to activity names.")
@click.option('-c', '--category', help = "The search string applied to category names.")
@click.option('-t', '--tag', help = 'The tags search string (e.g. "tag1 AND (tag2 OR tag3)".')
@click.option('-d', '--description', help = 'The description search string (e.g. "string1 OR (string2 AND string3).')
@click.option('-k', '--key', help = 'The database key of the fact.')
@pass_controler
def search(controler, start, end, activity, category, tag, description, key):
    """Fetch facts matching certain criteria."""
    # [FIXME]
    # Check what we actually match against.
    results = _search(controler, start, end, activity, category, tag, description, key)
    table, headers = _generate_facts_table(results)
    click.echo(tabulate(table, headers=headers))


def _search(controler, start = None, end = None, activity = None, category = None,
            tag = None, description = None, key = None):
    """
    Search facts machting given timerange and search term. Both are optional.

    Matching facts will be printed in a tabular representation.

    Make sure that arguments are converted into apropiate types before passing
    them on to the backend.

    We leave it to the backend to first parse the timeinfo and then complete any
    missing data based on the passed config settings.

    Args:
        search_term: Term that need to be matched by the fact in order to be considered a hit.
        time_range: Only facts within this timerange will be considered.
        tag: 
    """

    def search_facts(tree, search_list, search_attr, search_sub_attr = None):
        '''
        '''
        if len(tree) == 1:
            if isinstance(tree[0], (str, unicode)):
                l_term = tree[0]
                if search_sub_attr:
                    search_list = [fact for fact in search_list if l_term.lower() in getattr(getattr(fact, search_attr), search_sub_attr).lower()]
                else:
                    search_list = [fact for fact in search_list if getattr(fact, search_attr) is not None and l_term.lower() in getattr(fact, search_attr).lower()]
            else:
                search_list = search_facts(tree[0], search_list, search_attr, search_sub_attr)
        elif len(tree) == 3:
            l_term = tree[0]
            r_term = tree[2]
            op = tree[1]

            if isinstance(l_term, (str, unicode)):
                if search_sub_attr:
                    l_search_list = [fact for fact in search_list if l_term.lower() in getattr(getattr(fact, search_attr), search_sub_attr).lower()]
                else:
                    l_search_list = [fact for fact in search_list if getattr(fact, search_attr) is not None and l_term.lower() in getattr(fact, search_attr).name.lower()]
            else:
                l_search_list = search_facts(l_term, search_list, search_attr, search_sub_attr)

            if isinstance(r_term, (str, unicode)):
                if search_sub_attr:
                    r_search_list = [fact for fact in search_list if r_term.lower() in getattr(getattr(fact, search_attr), search_sub_attr).lower()]
                else:
                    r_search_list = [fact for fact in search_list if getattr(fact, search_attr) is not None and r_term.lower() in getattr(fact, search_attr).name.lower()]
            else:
                r_search_list = search_facts(r_term, search_list, search_attr, search_sub_attr)

            if op == 'AND':
                search_list = [x for x in l_search_list if x in r_search_list]
            elif op == 'OR':
                search_list = l_search_list
                search_list.extend(r_search_list)

        return search_list


    def search_tags(tree, search_list):
        '''
        '''
        if len(tree) == 1:
            if isinstance(tree[0], (str, unicode)):
                l_term = tree[0]
                search_list = [fact for fact in search_list if l_term.lower() in [x.name.lower() for x in fact.tags]]
            else:
                search_list = search_tags(tree[0], search_list)
        elif len(tree) == 3:
            l_term = tree[0]
            r_term = tree[2]
            op = tree[1]

            if isinstance(l_term, (str, unicode)):
                l_search_list = [fact for fact in search_list if l_term.lower() in [x.name.lower() for x in fact.tags]]
            else:
                l_search_list = search_tags(l_term, search_list)

            if isinstance(r_term, (str, unicode)):
                r_search_list = [fact for fact in search_list if r_term.lower() in [x.name.lower() for x in fact.tags]]
            else:
                r_search_list = search_tags(r_term, search_list)

            if op == 'AND':
                search_list = [x for x in l_search_list if x in r_search_list]
            elif op == 'OR':
                search_list = l_search_list
                search_list.extend(r_search_list)

        return search_list

    if key:
        results = [controler.facts.get(pk = key),]
    else:
        # Convert the start and time strings to datetimes.
        if start:
            start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M')
        if end:
            end = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M')

        results = controler.facts.get_all(start=start, end=end)

        if activity:
            identifier = pp.Word(pp.alphanums + pp.alphas8bit + '_' + '-')

            expr = pp.operatorPrecedence(baseExpr = identifier,
                                         opList = [("AND", 2, pp.opAssoc.LEFT, ),
                                                   ("OR", 2, pp.opAssoc.LEFT, ),])
            search_tree = expr.parseString(activity)

            results = search_facts(search_tree, results, 'activity', 'name')

        if category:
            identifier = pp.Word(pp.alphanums + pp.alphas8bit + '_' + '-')

            expr = pp.operatorPrecedence(baseExpr = identifier,
                                         opList = [("AND", 2, pp.opAssoc.LEFT, ),
                                                   ("OR", 2, pp.opAssoc.LEFT, ),])
            search_tree = expr.parseString(category)

            results = search_facts(search_tree, results, 'category', 'name')


        if tag:
            identifier = pp.Word(pp.alphanums + pp.alphas8bit + '_' + '-')

            expr = pp.operatorPrecedence(baseExpr = identifier,
                                         opList = [("AND", 2, pp.opAssoc.LEFT, ),
                                                   ("OR", 2, pp.opAssoc.LEFT, ),])
            search_tree = expr.parseString(tag)

            results = search_tags(search_tree, results)

        if description:
            identifier = pp.Word(pp.alphanums + pp.alphas8bit + '_' + '-')

            expr = pp.operatorPrecedence(baseExpr = identifier,
                                         opList = [("AND", 2, pp.opAssoc.LEFT, ),
                                                   ("OR", 2, pp.opAssoc.LEFT, ),])
            search_tree = expr.parseString(description)

            results = search_facts(search_tree, results, 'description')

    return results


@run.command(help=help_strings.LIST_HELP)
@click.option('-s', '--start', help = 'The start time string (e.g. "2017-01-01 00:00").')
@click.option('-e', '--end', help = 'The end time string (e.g. "2017-02-01 00:00").')
@pass_controler
def list(controler, start, end):
    """List all facts within a timerange."""
    results = _search(controler, start = start, end = end)
    table, headers = _generate_facts_table(results)
    click.echo(tabulate(table, headers=headers))


@run.command(help=help_strings.START_HELP)
@click.argument('raw_fact')
@click.argument('start', default='')
@click.argument('end', default='')
@pass_controler
def start(controler, raw_fact, start, end):
    """Start or add a fact."""
    # [FIXME]
    # The original semantics do not work anymore. As we make a clear difference
    # between *adding* a (complete) fact and *starting* a (ongoing) fact.
    # This needs to be reflected in this command.
    _start(controler, raw_fact, start, end)


def _start(controler, raw_fact, start, end):
    """
    Start or add a fact.

    Args:
        raw_fact: ``raw_fact`` containing information about the Fact to be started. As an absolute
            minimum this must be a string representing the 'activityname'.
        start (optional): When does the fact start?
        end (optional): When does the fact end?

    Returns:
        None: If everything went alright.

    Note:
        * Whilst it is possible to pass timeinformation as part of the ``raw_fact`` as
            well as dedicated ``start`` and ``end`` arguments only the latter will be represented
            in the resulting fact in such a case.
    """
    fact = Fact.create_from_raw_fact(raw_fact)

    # Explicit trumps implicit!
    if start:
        fact.start = time_helpers.parse_time(start)
    if end:
        fact.end = time_helpers.parse_time(end)

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

        timeframe = time_helpers.TimeFrame(
            fact.start.date(), fact.start.time(), end_date, end_time, None)
        fact.start, fact.end = time_helpers.complete_timeframe(timeframe, controler.config)

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


@run.command(help=help_strings.STOP_HELP)
@pass_controler
def stop(controler):
    """Stop tracking current fact. Saving the result."""
    _stop(controler)


def _stop(controler):
    """
    Stop cucrrent 'ongoing fact' and save it to the backend.

    Returns:
        None: If successful.

    Raises:
        ValueError: If no *ongoing fact* can be found.
    """
    try:
        fact = controler.facts.stop_tmp_fact()
    except ValueError:
        message = _(
            "Unable to continue temporary fact. Are you sure there is one?"
            "Try running *current*."
        )
        raise click.ClickException(message)
    else:
        #message = '{fact} ({duration} minutes)'.format(fact=str(fact), duration=fact.get_string_delta())
        start = fact.start.strftime("%Y-%m-%d %H:%M")
        end = fact.end.strftime("%Y-%m-%d %H:%M")
        fact_string = u'{0:s} to {1:s} {2:s}@{3:s}'.format(start, end, fact.activity.name, fact.category.name)
        message = "Stopped {fact} ({duration} minutes).".format(fact = fact_string,duration = fact.get_string_delta())
        controler.client_logger.info(_(message))
        click.echo(_(message))


@run.command(help=help_strings.CANCEL_HELP)
@pass_controler
def cancel(controler):
    """Cancel 'ongoing fact'. E.g stop it without storing in the backend."""
    _cancel(controler)


def _cancel(controler):
    """
    Cancel tracking current temporary fact, discaring the result.

    Returns:
        None: If success.

    Raises:
        KeyErŕor: No *ongoing fact* can be found.
    """
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


@run.command(help=help_strings.EXPORT_HELP)
@click.option('-s', '--start', help = 'The start time string (e.g. "2017-01-01 00:00").')
@click.option('-e', '--end', help = 'The end time string (e.g. "2017-02-01 00:00").')
@click.option('-a', '--activity', help = "The search string applied to activity names.")
@click.option('-c', '--category', help = "The search string applied to category names.")
@click.option('-t', '--tag', help = 'The tags search string (e.g. "tag1 AND (tag2 OR tag3)".')
@click.option('-d', '--description', help = 'The description search string (e.g. "string1 OR (string2 AND string3).')
@click.option('-k', '--key', help = 'The database key of the fact.')
@pass_controler
def remove(controler, start, end, activity, category, tag, description, key):
    """Export all facts of within a given timewindow to a file of specified format."""
    facts = _search(controler, start, end, activity, category, tag, description, key)
    table, headers = _generate_facts_table(facts)
    click.echo(tabulate(table, headers=headers))
    if click.confirm('Do you really want to delete the facts listed above?', abort = True):
        for cur_fact in facts:
            controler.facts.remove(cur_fact)


@run.command(help=help_strings.EXPORT_HELP)
@click.argument('tag_name', nargs=1, default = None)
@click.option('-s', '--start', help = 'The start time string (e.g. "2017-01-01 00:00").')
@click.option('-e', '--end', help = 'The end time string (e.g. "2017-02-01 00:00").')
@click.option('-a', '--activity', help = "The search string applied to activity names.")
@click.option('-c', '--category', help = "The search string applied to category names.")
@click.option('-t', '--tag', help = 'The tags search string (e.g. "tag1 AND (tag2 OR tag3)".')
@click.option('-d', '--description', help = 'The description search string (e.g. "string1 OR (string2 AND string3).')
@click.option('-k', '--key', help = 'The database key of the fact.')
@click.option('-r', '--remove', is_flag=True, help = 'Set this flag to remove the specified tag_name from the selected facts.')
@pass_controler
def tag(controler, tag_name, start, end, activity, category, tag, description, key, remove):
    """Export all facts of within a given timewindow to a file of specified format."""
    facts = _search(controler, start, end, activity, category, tag, description, key)
    table, headers = _generate_facts_table(facts)
    click.echo(tabulate(table, headers=headers))

    if remove:
        if click.confirm('Do you really want to REMOVE the tag #%s to the facts listed above?' % tag_name, abort = True):
            for cur_fact in facts:
                cur_fact.tags = [x for x in cur_fact.tags if x.name != tag_name]
                controler.facts._update(cur_fact)
    else:
        if click.confirm('Do you really want to ADD the tag #%s to the facts listed above?' % tag_name, abort = True):
            for cur_fact in facts:
                cur_fact.tags.append(hamster_lib.Tag(name = tag_name))
                controler.facts._update(cur_fact)


@run.command(help=help_strings.EXPORT_HELP)
@click.argument('key', nargs=1)
@click.option('-s', '--start', help = 'The new start time string (e.g. "2017-01-01 00:00").')
@click.option('-e', '--end', help = 'The new end time string (e.g. "2017-02-01 00:00").')
@click.option('-a', '--activity', help = "The new activity.")
@click.option('-c', '--category', help = "The new category.")
@click.option('-d', '--description', help = 'The new description.')
@pass_controler
def edit(controler, key, start, end, activity, category, description):
    """Export all facts of within a given timewindow to a file of specified format."""
    fact = controler.facts.get(pk = key)

    if fact:
        if start:
            start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M')
            fact.start = start

        if end:
            end = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M')
            fact.end = end

        if activity and category:
            fact.activity = hamster_lib.Activity(name = activity, category = category)
        elif activity or category:
            click.echo('Please specify an activity AND a category.')

        if description:
            fact.description = description

        controler.facts._update(fact)



@run.command(help=help_strings.EXPORT_HELP)
@click.argument('format', nargs=1, default='csv')
@click.argument('start', nargs=1, default='')
@click.argument('end', nargs=1, default='')
@click.option('-a', '--activity', help = "The search string applied to activity names.")
@click.option('-c', '--category', help = "The search string applied to category names.")
@click.option('-t', '--tag', help = 'The tags search string (e.g. "tag1 AND (tag2 OR tag3)".')
@click.option('-d', '--description', help = 'The description search string (e.g. "string1 OR (string2 AND string3).')
@click.option('-k', '--key', help = 'The database key of the fact.')
@click.option('-f', '--filename', help = "The filename where to store the export file.")
@pass_controler
def export(controler, format, start, end, activity, category, tag, description, key, filename):
    """Export all facts of within a given timewindow to a file of specified format."""
    _export(controler, format, start, end, activity, category, tag, description, key, filename)


def _export(controler, format, start, end, activity = None, category = None, tag = None, description = None, filename = None):
    """
    Export all facts in the given timeframe in the format specified.

    Args:
        format (str): Format to export to. Valid options are: ``csv``, ``xml`` and ``ical``.
        start (datetime.datetime): Consider only facts starting at this time or later.
        end (datetime.datetime): Consider only facts starting no later than this time.

    Returns:
        None: If everything went alright.

    Raises:
        click.Exception: If format is not recognized.
    """
    accepted_formats = ['csv', 'tsv', 'ical', 'xml']
    # [TODO]
    # Once hamster_lib has a proper 'export' register available we should be able
    # to streamline this.
    if format not in accepted_formats:
        message = _("Unrecocgnized export format recieved")
        controler.client_logger.info(message)
        raise click.ClickException(message)
    if not start:
        start = None
    if not end:
        end = None

    if filename:
        filepath = filename
    else:
        filepath = controler.client_config['export_path']
        filepath = filepath + '.' + format

    #facts = controler.facts.get_all(start=start, end=end)
    facts = _search(controler,
                    activity = activity,
                    category = category,
                    tag = tag,
                    description = description)

    if format == 'csv':
        writer = reports.CSVWriter(filepath)
        writer.write_report(facts)
        click.echo(_("Facts have been exported to: {path}".format(path=filepath)))
    elif format == 'tsv':
        writer = reports.TSVWriter(filepath)
        writer.write_report(facts)
        click.echo(_("Facts have been exported to: {path}".format(path=filepath)))
    elif format == 'ical':
        writer = reports.ICALWriter(filepath)
        writer.write_report(facts)
        click.echo(_("Facts have been exported to: {path}".format(path=filepath)))
    elif format == 'xml':
        writer = reports.XMLWriter(filepath)
        writer.write_report(facts)
        click.echo(_("Facts have been exported to: {path}".format(path=filepath)))


@run.command(help=help_strings.CATEGORIES_HELP)
@pass_controler
def categories(controler):
    """List all existing categories, ordered by name."""
    _categories(controler)


def _categories(controler):
    """
    List all existing categories, ordered by name.

    Returns:
        None: If success.
    """
    result = controler.categories.get_all()
    # [TODO]
    # Provide nicer looking tabulated output.
    for category in result:
        click.echo(category.name)


@run.command(help=help_strings.CURRENT_HELP)
@pass_controler
def current(controler):
    """Display current *ongoing fact*."""
    _current(controler)


def _current(controler):
    """
    Return current *ongoing fact*.

    Returns:
        None: If everything went alright.

    Raises:
        click.ClickException: If we fail to fetch any *ongoing fact*.
    """
    try:
        fact = controler.facts.get_tmp_fact()
    except KeyError:
        message = _(
            "There seems no be no activity beeing tracked right now."
            " maybe you want to *start* tracking one right now?"
        )
        raise click.ClickException(message)
    else:
        fact.end = datetime.datetime.now()
        string = '{fact} ({duration} minutes)'.format(fact=fact, duration=fact.get_string_delta())
        click.echo(string)


@run.command(help=help_strings.ACTIVITIES_HELP)
@click.argument('search_term', default='')
@pass_controler
def activities(controler, search_term):
    """List all activities. Provide optional filtering by name."""
    _activities(controler, search_term)


def _activities(controler, search_term):
    """
    List all activities. Provide optional filtering by name.

    Args:
        search_term (str): String to match ``Activity.name`` against.

    Returns:
        None: If success.
    """
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


@run.command(help=help_strings.LICENSE_HELP)
def license():
    """Show license information."""
    _license()


def _license():
    """Show license information."""
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


@run.command(help=help_strings.DETAILS_HELP)
@pass_controler
def details(controler):
    """List details about the runtime environment."""
    _details(controler)


def _details(controler):
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
        Process client section of provided config and turn it into proper config dictionary.

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
            if store not in hamster_lib.lib.REGISTERED_BACKENDS.keys():
                raise ValueError(_("Unrecognized store option."))
            return store

        def get_db_path():
            return config.get('Backend', 'db_path')

        def get_fact_min_delta():
            return config.get('Backend', 'fact_min_delta')

        def get_tmpfile_path():
            """Return path to file used to store *ongoing fact*."""
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
        'key': _("Key"),
        'start': _("Start"),
        'end': _("End"),
        'activity': _("Activity"),
        'category': _("Category"),
        'tags': _("Tags"),
        'description': _("Description"),
        'delta': _("Duration")
    }

    columns = ('key', 'start', 'end', 'activity', 'category', 'tags', 'description',
        'delta')

    header = [headers[column] for column in columns]

    TableRow = namedtuple('TableRow', columns)

    table = []
    for fact in facts:
        if fact.category:
            category = fact.category.name
        else:
            category = ''

        if fact.tags:
            tags = '#'
            tags += '#'.join(sorted([x.name + ' ' for x in fact.tags]))
        else:
            tags = ''

        table.append(TableRow(
            key = fact.pk,
            activity=fact.activity.name,
            category=category,
            description=fact.description,
            tags=tags,
            start=fact.start.strftime('%Y-%m-%d %H:%M'),
            end=fact.end.strftime('%Y-%m-%d %H:%M'),
            # [TODO]
            # Use ``Fact.get_string_delta`` instead!
            delta='{minutes} min.'.format(minutes=(int(fact.delta.total_seconds() / 60))),
        ))

    return (table, header)


def _show_greeting():
    """Display a greeting message providing basic set of information."""
    click.echo(_("Welcome to 'hamster_cli', your friendly time tracker for the command line."))
    click.echo("Copyright (C) 2015-2016, Eric Goller <elbenfreund@DenkenInEchtzeit.net>")
    click.echo(_(
        "'hamster_cli' is published under the terms of the GPL3, for details please use"
        "the 'license' command."
    ))
    click.echo()
