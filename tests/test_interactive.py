import pytest
import duckdb
from pksql.interactive import PKSQLShell


def create_parquet(path, rows=1):
    """Utility to create a simple parquet file using duckdb."""
    duckdb.sql(f"COPY (SELECT range AS id FROM range({rows})) TO '{path}' (FORMAT PARQUET)")


def test_alias_and_query(tmp_path, capsys):
    file_path = tmp_path / "data.parquet"
    create_parquet(file_path)

    shell = PKSQLShell()
    shell.do_alias(f"mydata {file_path}")
    shell.default("SELECT COUNT(*) FROM mydata")

    captured = capsys.readouterr()
    assert "Alias mydata registered" in captured.out
    assert "1" in captured.out
    assert "Query time" in captured.err


def test_unalias(tmp_path, capsys):
    file_path = tmp_path / "data.parquet"
    create_parquet(file_path)

    shell = PKSQLShell()
    shell.do_alias(f"mydata {file_path}")
    shell.do_unalias("mydata")

    captured = capsys.readouterr().out
    assert "Alias mydata removed." in captured
    assert "mydata" not in shell.file_aliases


def test_glob_lists_files(tmp_path, capsys):
    paths = []
    for i in range(3):
        p = tmp_path / f"file{i}.parquet"
        create_parquet(p)
        paths.append(str(p))

    pattern = tmp_path / "*.parquet"
    shell = PKSQLShell()
    shell.do_glob(str(pattern))
    out = capsys.readouterr().out
    assert "Found" in out
    for p in paths:
        assert p in out


def test_do_exit_closes_connection(capsys):
    shell = PKSQLShell()
    assert shell.do_exit("") is True
    assert "Goodbye" in capsys.readouterr().out
    # The connection should be closed; further queries must fail.
    with pytest.raises(Exception):
        shell.conn.sql("SELECT 1")


def test_do_eof_exits_and_closes(capsys):
    shell = PKSQLShell()
    assert shell.do_EOF("") is True
    assert "Goodbye" in capsys.readouterr().out
    with pytest.raises(Exception):
        shell.conn.sql("SELECT 1")


def test_alias_glob_no_match_warns_and_does_not_register(tmp_path, capsys):
    shell = PKSQLShell()
    pattern = tmp_path / "missing_*.parquet"
    shell.do_alias(f"empty '{pattern}'")
    out = capsys.readouterr().out
    assert "No files currently match pattern" in out
    # An empty glob must not leave a half-registered, unqueryable alias behind.
    assert "empty" not in shell.file_aliases


def test_alias_remote_path_skips_glob_check(capsys):
    shell = PKSQLShell()
    # A remote glob can't be validated locally; it must not trip the
    # "no files match" warning (view creation will fail without httpfs, which
    # is fine — we're only asserting the local glob check is skipped).
    shell.do_alias("remote 's3://bucket/data_*.parquet'")
    assert "No files currently match pattern" not in capsys.readouterr().out


def test_alias_with_spaces(tmp_path, capsys):
    dir_path = tmp_path / "with space"
    dir_path.mkdir()
    file_path = dir_path / "data.parquet"
    create_parquet(file_path)

    shell = PKSQLShell()
    shell.do_alias(f"mydata '{file_path}'")
    shell.default("SELECT COUNT(*) FROM mydata")

    out = capsys.readouterr().out
    assert "Alias mydata registered" in out
    assert "1" in out
