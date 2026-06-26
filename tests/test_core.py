import json
from datetime import date

import duckdb

from pksql.core import execute_query, format_elapsed, json_serializer, render_result


def test_execute_query_table():
    output, time_str = execute_query("SELECT 1 AS a")
    assert "1" in output
    assert isinstance(time_str, str)


def test_execute_query_csv_and_tsv():
    output_csv, _ = execute_query("SELECT 1 AS a, 2 AS b", output_format="csv")
    assert "a,b" in output_csv
    assert "1,2" in output_csv

    output_tsv, _ = execute_query("SELECT 1 AS a, 2 AS b", output_format="tsv")
    assert "a\tb" in output_tsv
    assert "1\t2" in output_tsv


def test_execute_query_csv_escapes_and_nulls():
    # A value containing the delimiter must be quoted, and SQL NULL must render
    # as an empty field (not the literal "None").
    output, _ = execute_query("SELECT 'c,d' AS x, NULL AS y", output_format="csv")
    assert output == 'x,y\n"c,d",'

    # The tsv writer quotes values that contain a tab.
    output_tsv, _ = execute_query("SELECT e'a\tb' AS x", output_format="tsv")
    assert output_tsv == 'x\n"a\tb"'


def test_execute_query_json_uses_serializer():
    # DATE values are not natively JSON-serializable; the custom serializer
    # should turn them into ISO strings rather than raising.
    output, _ = execute_query("SELECT DATE '2020-01-01' AS d", output_format="json")
    assert json.loads(output) == [{"d": "2020-01-01"}]


def test_execute_query_non_query_returns_none():
    conn = duckdb.connect(database=":memory:")
    output, time_str = execute_query("CREATE TABLE t (id INTEGER)", conn=conn)
    assert output is None
    assert isinstance(time_str, str)


def test_execute_query_with_cte_is_treated_as_query():
    # Regression guard: a WITH ... SELECT statement produces a result set and
    # must be rendered, not reported as a bare "executed successfully".
    output, _ = execute_query("WITH x AS (SELECT 1 AS a) SELECT * FROM x")
    assert "1" in output


def test_render_result_unknown_format_returns_none():
    result = duckdb.sql("SELECT 1 AS a")
    assert render_result(result, "xml") is None


def test_json_serializer_handles_date_and_bytes():
    assert json_serializer(date(2020, 1, 1)) == "2020-01-01"
    assert isinstance(json_serializer(b"abc"), str)


def test_format_elapsed_units():
    assert format_elapsed(0.0000001).endswith("μs")
    assert format_elapsed(0.01).endswith("ms")
    assert format_elapsed(2.5).endswith("sec")
