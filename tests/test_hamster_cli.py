# -*- coding: utf-8 -*-

import pytest
from click import testing
from hamster_cli import hamster_cli


@pytest.fixture
def run_app():
    def runner(args=[]):
        return testing.CliRunner().invoke(hamster_cli.run, args)
    return runner


def test_smoke(run_app):
    runner = testing.CliRunner()
    result = run_app(['--help'])
    assert result.exit_code == 0

class TestList():
    # [FIXME]
    def test_list(self, run_app):
        result = run_app(['list'])
        assert result.exit_code == 0
        print(result.__dict__)

