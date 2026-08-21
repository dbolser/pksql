from pathlib import Path

import duckdb
import pytest

from pksql import aliases


def test_parse_reads_names_comments_and_quotes():
    parsed = aliases.parse(
        "\n".join(
            [
                "# a comment",
                "",
                "corpus = data/corpus.duckdb",
                "hits   = 'results/*.parquet'",
                "odd = data/a=b.parquet",
            ]
        )
    )
    assert parsed == {
        "corpus": "data/corpus.duckdb",
        "hits": "results/*.parquet",
        "odd": "data/a=b.parquet",
    }


@pytest.mark.parametrize(
    "text",
    [
        "corpus data/corpus.duckdb",  # no '='
        "drop table x = y",  # not an identifier
        "corpus =",  # no path
    ],
)
def test_parse_rejects_malformed_lines(text):
    with pytest.raises(aliases.AliasError):
        aliases.parse(text)


def test_resolve_anchors_relative_paths_to_the_declaring_file():
    assert aliases.resolve("data/x.parquet", Path("/proj")) == "/proj/data/x.parquet"
    assert aliases.resolve("/abs/x.parquet", Path("/proj")) == "/abs/x.parquet"
    assert aliases.resolve("s3://b/x.parquet", Path("/proj")) == "s3://b/x.parquet"


def test_local_aliases_add_to_and_override_global(workspace, tmp_path):
    home = Path.home()
    (home / ".pksql").write_text("shared = shared.parquet\ncorpus = global.duckdb\n")
    (workspace / ".pksql").write_text("corpus = local.duckdb\n")

    loaded = aliases.load()
    assert loaded == {
        "shared": str(home / "shared.parquet"),
        "corpus": str(workspace / "local.duckdb"),
    }


def test_home_directory_alias_file_is_read_once(workspace):
    home = Path.home()
    (home / ".pksql").write_text("corpus = corpus.duckdb\n")
    assert aliases.source_files(cwd=home) == [home / ".pksql"]


def test_update_file_preserves_comments_and_position(workspace):
    path = workspace / ".pksql"
    path.write_text("# notes\ncorpus = old.duckdb\nhits = hits.parquet\n")

    assert aliases.update_file(path, "corpus", "new.duckdb") == "old.duckdb"
    assert path.read_text() == "# notes\ncorpus = new.duckdb\nhits = hits.parquet\n"

    assert aliases.update_file(path, "hits", None) == "hits.parquet"
    assert path.read_text() == "# notes\ncorpus = new.duckdb\n"

    assert aliases.update_file(path, "extra", "extra.parquet") is None
    assert path.read_text().endswith("extra = extra.parquet\n")


def test_update_file_creates_a_missing_file(workspace):
    path = workspace / ".pksql"
    assert aliases.update_file(path, "corpus", "corpus.duckdb") is None
    assert path.read_text() == "corpus = corpus.duckdb\n"


def test_create_views_skips_paths_that_do_not_bind(workspace):
    duckdb.sql(f"COPY (SELECT 1 AS a) TO '{workspace / 'good.parquet'}'")
    conn = duckdb.connect(database=":memory:")

    failed = aliases.create_views(
        conn,
        {"good": str(workspace / "good.parquet"), "dead": "/nowhere/dead.parquet"},
    )

    assert failed == ["dead"]
    assert conn.sql("SELECT * FROM good").fetchall() == [(1,)]
    conn.close()


def test_create_views_quotes_paths_containing_quotes(workspace):
    path = workspace / "it's data.parquet"
    duckdb.sql(f"COPY (SELECT 1 AS a) TO '{str(path).replace(chr(39), chr(39) * 2)}'")
    conn = duckdb.connect(database=":memory:")

    assert aliases.create_views(conn, {"quoted": str(path)}) == []
    assert conn.sql("SELECT * FROM quoted").fetchall() == [(1,)]
    conn.close()


@pytest.mark.parametrize("name", ["corpus", "hits2", "_x", "filter", "database"])
def test_is_usable_name_accepts_ordinary_identifiers(name):
    assert aliases.is_usable_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "select",  # reserved
        "asof",  # type_function, which DuckDB also rejects unquoted
        "1st",  # not an identifier at all
        "drop table x",
        "",
    ],
)
def test_is_usable_name_rejects_what_duckdb_cannot_use(name):
    assert not aliases.is_usable_name(name)


def test_update_file_refuses_a_malformed_file(workspace):
    path = workspace / ".pksql"
    path.write_text("this is junk\n")
    with pytest.raises(aliases.AliasError):
        aliases.update_file(path, "corpus", "corpus.duckdb")
    assert path.read_text() == "this is junk\n"


def test_missing_only_checks_local_paths(workspace):
    (workspace / "there.parquet").touch()
    assert not aliases.missing(str(workspace / "there.parquet"))
    assert aliases.missing(str(workspace / "gone.parquet"))
    assert aliases.missing(str(workspace / "*.csv"))
    assert not aliases.missing(str(workspace / "*.parquet"))
    assert not aliases.missing("s3://bucket/never-checked.parquet")
