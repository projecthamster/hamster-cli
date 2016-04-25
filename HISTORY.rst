.. :changelog:

History
-------

0.12.0 (2016-04-25)
-------------------
* ``stop`` now shows detail on the fact saved.
* ``current`` now shows how much time was accumulated so far.
* Remove standalone script block. You are expected to utilize pip/setuptools to
  setup ``hamster_cli``. ``virtualenvs`` FTW!
* Testenvironment now uses linkchecks and ``doc8`` for validating the
  documentation.
* Removed 'GTK window' related pseudo methods. Until the functionality is
  actually here.
* Added ``manifest`` validation to testenvironment.
* Added ``pep257`` validation to testsuite.
* Vastly improved docstring, docstringcoverage and frontend helptexts.
* Use ``hamsterlib 0.10.0`` new improved config layout.
* Add GPL boilerplate and frontend information.
* ``release`` make target now uses ``twine``.
* Provide new ``details`` command to list basic runtime environment details.

0.11.0 (2016-04-16)
--------------------
* New, solid config handling.
* Switch to `semantic versioning <http://semver.org>`_.
* Move CI from codeship to Travis-CI.
* First batch of very basic integration tests.
* Several fixes to packaging.

0.1.0 (2016-04-09)
---------------------
* First release on PyPI.
* Prove-of-concept release.
* Most of the basic functionality is there.
* Provides basic test coverage.
