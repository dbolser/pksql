import time
from typing import Optional, Tuple

import duckdb


def execute_query(sql: str, output_format: str = "table", conn: Optional[duckdb.DuckDBPyConnection] = None) -> Tuple[str, str]:
    """Execute a SQL query using DuckDB and return formatted output and timing.

    Parameters
    ----------
    sql : str
        SQL statement to execute.
    output_format : str, optional
        One of ``"table"``, ``"csv"`` or ``"tsv"``.
    conn : duckdb.DuckDBPyConnection, optional
        Existing connection to use. If ``None`` a new in-memory connection is
        created for the query.

    Returns
    -------
    Tuple[str, str]
        A tuple ``(output, time_str)`` where ``output`` contains the formatted
        result or confirmation message and ``time_str`` contains the formatted
        elapsed time.
    """
    local_conn = conn or duckdb.connect(database=":memory:")

    start_time = time.time()
    result = local_conn.sql(sql)

    # Determine if we should expect results to display
    is_query = sql.strip().lower().startswith(
        ("select", "show", "describe", "explain", "with", "insert", "update", "delete")
    ) or bool(result.columns)

    output_lines = []
    if output_format == "table":
        if is_query:
            output_lines.append(str(result))
        else:
            output_lines.append("Query executed successfully.")
    else:
        delimiter = "," if output_format == "csv" else "\t"
        if is_query:
            header = delimiter.join(result.columns)
            output_lines.append(header)
            for row in result.fetchall():
                output_lines.append(delimiter.join(map(str, row)))
        else:
            output_lines.append("Query executed successfully.")

    end_time = time.time()
    elapsed = end_time - start_time

    if elapsed < 0.001:
        time_str = f"{elapsed*1000000:.2f} μs"
    elif elapsed < 1:
        time_str = f"{elapsed*1000:.2f} ms"
    else:
        time_str = f"{elapsed:.3f} sec"

    return "\n".join(output_lines), time_str
