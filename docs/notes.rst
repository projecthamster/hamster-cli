Implementation and Development Notes
=====================================

To promote cleanness and seperation of concens we split the actual command
invocation and its click-integration from the logic ctriggered by that
that command. This has the added benefit of a clear seperation of unit and
integration tests.

* For information about unicode handling, see:
  http://click.pocoo.org/5/python3/#python3-surrogates This should be alright for
  our usecase, as any properly user environment should have its unicode locale declared.
  And if not, its acceptable to bully the user to do so.

* Click commands deal only with strings. So quite often, the first thing our
  custom command-functions will do is provide some basic type conversion and
  error checking. before calling the corresponding lib method.
* Whilst the backend usualy either returns results or Errors, the client should
  always try to handle those errors which are predictable and turn them into user
  relevant command line output. Only actual errors that are not part of the expected
  user interaction shall get through as exceptions.
