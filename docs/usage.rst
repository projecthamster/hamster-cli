========
Usage
========

To use hamster_cli simply imvoke it::

    hamster-cli

Incompabilities
---------------

We tries hard to stay compatible with *legacy hamster-cli* but there are some aspects where we
could not do so without make to huge tradeoffs to what we feel is the proper way to do so.
For transparency and you to evaluate if those breaking points affect you we list them here:

* Only one *ongoing fact* at a time. You will not be able to start more than one fact without
  providing an endtime. If you do you will be presented with an error and either have to cancel or
  stop the current *ongoing fact*.
* Argument values that contain whitespaces need to be wrapped in quoteation marks. This is
  established practice and needed to stay POSIX compatible. In particular this affects:
  * start/end - datetimes; As date and time aspects are seperatetd by a whitespace.
  * ``raw_fact`` arguments; As they contain various whitespaces.
  * search terms
