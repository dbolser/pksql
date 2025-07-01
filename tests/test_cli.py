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


def test_cli_csv_output():
    runner = CliRunner()
    result = runner.invoke(cli, ["--output-format", "csv", "SELECT 1 AS a, 2 AS b"])
    assert result.exit_code == 0
    # CSV header and row should be printed
    assert "a,b" in result.output
    assert "1,2" in result.output


def test_cli_tsv_output():
    runner = CliRunner()
    result = runner.invoke(cli, ["--output-format", "tsv", "SELECT 1 AS a, 2 AS b"])
    assert result.exit_code == 0
    # TSV header and row should be printed with tab separation
    assert "a\tb" in result.output
    assert "1\t2" in result.output


def test_cli_invalid_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["SELECT", "*"])
    # Invalid SQL should cause non-zero exit code
    assert result.exit_code != 0
    assert "Error" in result.output
