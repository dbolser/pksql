import json
from pathlib import Path

import duckdb
import pytest
from click.testing import CliRunner

from pksql import aliases
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
    assert "Query time" in result.stderr


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


def test_cli_json_output():
    runner = CliRunner()
    result = runner.invoke(cli, ["-F", "json", "SELECT 1 AS a, 2 AS b"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == [{"a": 1, "b": 2}]


def test_cli_invalid_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["SELECT", "*"])
    # Invalid SQL should cause non-zero exit code
    assert result.exit_code != 0
    assert "Error" in result.stderr


def _parquet(path, sql="SELECT 1 AS a"):
    path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    return path


def test_add_alias_then_query_it(workspace):
    _parquet(workspace / "data" / "corpus.parquet", "SELECT 42 AS answer")
    runner = CliRunner()

    added = runner.invoke(cli, ["add-alias", "corpus", "=", "data/corpus.parquet"])
    assert added.exit_code == 0
    assert (workspace / ".pksql").read_text() == "corpus = data/corpus.parquet\n"

    result = runner.invoke(cli, ["-F", "csv", "SELECT * FROM corpus"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "answer\n42"


def test_add_alias_accepts_all_assignment_spellings(workspace):
    runner = CliRunner()
    for words in (["a", "x.parquet"], ["b", "=", "x.parquet"], ["c=x.parquet"]):
        assert runner.invoke(cli, ["add-alias", *words]).exit_code == 0
    assert aliases.parse((workspace / ".pksql").read_text()) == {
        "a": "x.parquet",
        "b": "x.parquet",
        "c": "x.parquet",
    }


def test_add_alias_warns_when_nothing_matches(workspace):
    result = CliRunner().invoke(cli, ["add-alias", "gone", "/nowhere/gone.parquet"])
    assert result.exit_code == 0
    assert "nothing matches" in result.stderr


@pytest.mark.parametrize("name", ["drop table x", "1st", "a-b"])
def test_add_alias_rejects_a_name_that_is_not_an_identifier(workspace, name):
    result = CliRunner().invoke(cli, ["add-alias", name, "=", "y.parquet"])
    assert result.exit_code == 1
    assert "not a valid alias name" in result.stderr
    assert not (workspace / ".pksql").exists()


@pytest.mark.parametrize("name", ["select", "asof"])
def test_a_keyword_alias_works_when_the_query_quotes_it(workspace, name):
    _parquet(workspace / "kw.parquet", "SELECT 5 AS v")
    runner = CliRunner()

    added = runner.invoke(cli, ["add-alias", name, "kw.parquet"])
    assert added.exit_code == 0
    assert "must quote it" in added.stderr

    quoted = runner.invoke(cli, ["-F", "csv", f'SELECT * FROM "{name}"'])
    assert quoted.exit_code == 0
    assert quoted.stdout.strip() == "v\n5"


def test_mutating_a_malformed_alias_file_is_refused(workspace):
    path = workspace / ".pksql"
    path.write_text("this is junk\n")
    runner = CliRunner()

    for args in (["add-alias", "good", "good.parquet"], ["rm-alias", "good"]):
        result = runner.invoke(cli, args)
        assert result.exit_code == 1
        assert "expected 'name = path'" in result.stderr
    # Refused, not half-applied.
    assert path.read_text() == "this is junk\n"


def test_mutating_past_a_malformed_entry_reports_rather_than_crashes(workspace):
    (workspace / ".pksql").write_text("corpus =\n")
    result = CliRunner().invoke(cli, ["rm-alias", "corpus"])
    assert result.exit_code == 1
    assert "has no path" in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_global_alias_is_visible_from_any_directory(workspace):
    _parquet(Path.home() / "shared.parquet", "SELECT 7 AS n")
    runner = CliRunner()

    added = runner.invoke(cli, ["add-alias", "--global", "shared", "shared.parquet"])
    assert added.exit_code == 0
    assert (Path.home() / ".pksql").read_text() == "shared = shared.parquet\n"

    result = runner.invoke(cli, ["-F", "csv", "SELECT * FROM shared"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "n\n7"


def test_a_dead_alias_does_not_break_other_queries(workspace):
    _parquet(workspace / "good.parquet", "SELECT 1 AS a")
    (workspace / ".pksql").write_text(
        "good = good.parquet\ndead = /nowhere/dead.parquet\n"
    )
    runner = CliRunner()

    assert runner.invoke(cli, ["-F", "csv", "SELECT * FROM good"]).exit_code == 0

    named = runner.invoke(cli, ["SELECT * FROM dead"])
    assert named.exit_code == 1
    assert "does not exist" in named.stderr


def test_malformed_alias_file_is_reported(workspace):
    (workspace / ".pksql").write_text("this is not an alias\n")
    result = CliRunner().invoke(cli, ["SELECT 1"])
    assert result.exit_code == 1
    assert "expected 'name = path'" in result.stderr


def test_rm_alias(workspace):
    (workspace / ".pksql").write_text("corpus = corpus.parquet\n")
    runner = CliRunner()

    removed = runner.invoke(cli, ["rm-alias", "corpus"])
    assert removed.exit_code == 0
    assert (workspace / ".pksql").read_text() == ""

    missing = runner.invoke(cli, ["rm-alias", "corpus"])
    assert missing.exit_code == 1
    assert "is not in" in missing.stderr


def test_aliases_lists_sources_and_flags_missing_paths(workspace):
    _parquet(workspace / "good.parquet")
    (workspace / ".pksql").write_text(
        "good = good.parquet\ndead = /nowhere/dead.parquet\n"
    )

    result = CliRunner().invoke(cli, ["aliases"])
    assert result.exit_code == 0
    assert str(workspace / ".pksql") in result.output
    assert "good = good.parquet" in result.output
    assert "dead = /nowhere/dead.parquet (missing)" in result.output


def test_aliases_when_none_registered(workspace):
    result = CliRunner().invoke(cli, ["aliases"])
    assert result.exit_code == 0
    assert "No aliases registered" in result.output
