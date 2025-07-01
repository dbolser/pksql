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

    captured = capsys.readouterr().out
    assert "Alias mydata registered" in captured
    assert "1" in captured
    assert "Query time" in captured


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
