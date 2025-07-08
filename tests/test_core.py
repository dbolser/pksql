from pksql.core import execute_query


def test_execute_query_table():
    output, time_str = execute_query("SELECT 1 AS a")
    assert "1" in output
    assert isinstance(time_str, str)


def test_execute_query_csv_tsv():
    output_csv, _ = execute_query("SELECT 1 AS a, 2 AS b", output_format="csv")
    assert "a,b" in output_csv
    assert "1,2" in output_csv

    output_tsv, _ = execute_query("SELECT 1 AS a, 2 AS b", output_format="tsv")
    assert "a\tb" in output_tsv
    assert "1\t2" in output_tsv
