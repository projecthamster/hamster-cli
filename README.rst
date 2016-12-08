===============================
hamster_cli
===============================

.. image:: https://img.shields.io/pypi/v/hamster_cli.svg
        :target: https://pypi.python.org/pypi/hamster_cli

.. image:: https://img.shields.io/travis/elbenfreund/hamster_cli/master.svg
        :target: https://travis-ci.org/elbenfreund/hamster_cli

.. image:: https://img.shields.io/codecov/c/gh/projecthamster/hamster_cli/master.svg
        :target: https://codecov.io/gh/projecthamster/hamster-cli

.. image:: https://readthedocs.org/projects/hamst-cli/badge/?version=master
        :target: https://readthedocs.org/projects/hamst-cli/badge/?version=master
        :alt: Documentation Status

.. image:: https://badge.waffle.io/elbenfreund/hamster_cli.png?label=ready&title=Ready
        :target: https://waffle.io/elbenfreund/hamster_cli
        :alt: 'Stories in Ready'

.. image:: https://requires.io/github/elbenfreund/hamster_cli/requirements.svg?branch=master
        :target: https://requires.io/github/elbenfreund/hamster_cli/requirements/?branch=master
        :alt: Requirements Status



A basic CLI for the hamster time tracker.

*WARNING*
This is still pre-alpha software. Altough we are reaching apoint were most
things work as intended we make no promisse about your data as well as any
commitment. In particular there is no intension to migrate any databases from
this version to any future more mature release.

News (2016-04-25)
-----------------
Version 0.12.0 is out! With this version we feel confident that you may be able
to actually play with ``hamster-cli`` in a somewhat productive way. Whilst we
are still far from being production ready and miss a significant amount of
legacy feature this release may give you quite the idea where we are heading.
For the first time we were able to give the frontend some love whilst further
beefin up our QA toolchain, introducing even more tests and new test
environments. The documentation has been vastly improved, digging into the code
never was easier.

Happy hacking; Eric.

Features
--------
* High test coverage.
* Well documented.
* Lightweight.
* Free software: GPL3
* Uses ``hamsterlib``, which supports a wide array of databases.
* Few dependencies
* Active development.

Resources
-----------
* `Documentation <https://hamst-cli.readthedocs.org/en/master/>`_


Usage
-----------

 * /usr/bin/hamster-cli start ACTIVITY [START_TIME[-END_TIME]]
 * /usr/bin/hamster-cli stop
 * /usr/bin/hamster-cli list [START_TIME[-END_TIME]]

Actions:
    * start (default): Start tracking an activity.
    * stop: Stop tracking current activity.
    * list: List activities.
    * list-activities: List all the activities names, one per line.
    * list-categories: List all the categories names, one per line.

Time formats:

'YYYY-MM-DD hh:mm:ss': Absolute time. Defaulting to 0 for the time values missing, and current day for date values. E.g. (considering 2010-03-09 16:30:20 as current date, time):

   * 2010-03 13:15:40 is 2010-03-09 13:15:40
   * 2010-03-09 13:15 is 2010-03-09 13:15:00
   * 2010-03-09 13    is 2010-03-09 00:13:00
   * 2010-02 13:15:40 is 2010-02-09 13:15:40
   * 13:20            is 2010-03-09 13:20:00
   * 20               is 2010-03-09 00:20:00

'-hh:mm:ss': Relative time. From the current date and time. Defaulting to 0 for the time values missing, same as in absolute time.


Credits
---------
Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-pypackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
