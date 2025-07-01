import pytest
import duckdb

from click.testing import CliRunner
from pksql.main import cli


def test_cli_shows_help_when_no_args():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    # Click prints usage line at top when showing help
    assert "Usage" in result.output


def test_cli_simple_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["SELECT 1 AS a"])
    assert result.exit_code == 0
    assert "1" in result.output
    assert "Query time" in result.output


def test_cli_invalid_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["SELECT", "*"])
    # Invalid SQL should cause non-zero exit code
    assert result.exit_code != 0
    assert "Error" in result.output
