"""Shared query-execution helpers for pksql.

Both the direct-query CLI (``pksql.main``) and the interactive shell
(``pksql.interactive``) need to run a SQL statement, render the result for a
given output format and report how long it took.  Keeping that logic here
avoids duplicating it (and lets both entry points agree on what counts as a
result-producing query).
"""

import base64
import csv
import io
import json
import time
from datetime import date, datetime
from datetime import time as time_type
from decimal import Decimal

import duckdb


def json_serializer(obj):
    """Custom JSON serializer for objects ``json`` can't handle natively."""
    if isinstance(obj, (datetime, date, time_type)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        # Convert binary data to a base64 string.
        return base64.b64encode(obj).decode("utf-8")
    # Fallback for any other non-serializable types.
    return str(obj)


def format_elapsed(elapsed):
    """Format an elapsed time (in seconds) as a human-readable string."""
    if elapsed < 0.001:
        return f"{elapsed * 1000000:.2f} μs"
    if elapsed < 1:
        return f"{elapsed * 1000:.2f} ms"
    return f"{elapsed:.3f} sec"


def render_result(result, output_format):
    """Render a DuckDB result for ``output_format``.

    Returns the text to print to stdout, or ``None`` when the statement
    produced no result set (e.g. DDL such as ``CREATE``/``COPY``), in which
    case the caller decides how to report success.
    """
    is_query = (
        result is not None and hasattr(result, "columns") and bool(result.columns)
    )
    if not is_query:
        return None

    if output_format == "table":
        # DuckDB renders a nicely boxed table via its string representation.
        return str(result)
    if output_format in ("csv", "tsv"):
        delimiter = "," if output_format == "csv" else "\t"
        # Use the stdlib csv writer so values containing the delimiter, quotes
        # or newlines are quoted/escaped correctly, and SQL NULL becomes an
        # empty field rather than the literal string "None".
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
        writer.writerow(result.columns)
        writer.writerows(result.fetchall())
        return buffer.getvalue().rstrip("\n")
    if output_format == "json":
        rows = [dict(zip(result.columns, row)) for row in result.fetchall()]
        return json.dumps(rows, default=json_serializer)
    return None


def execute_query(sql, conn=None, output_format="table"):
    """Execute ``sql`` and return ``(output, time_str)``.

    ``output`` is the rendered result text for a result-producing query, or
    ``None`` for statements that return no rows (callers decide how to report
    success).  ``conn`` defaults to DuckDB's global in-memory connection.
    ``time_str`` is the formatted elapsed execution time.
    """
    executor = conn if conn is not None else duckdb
    # perf_counter is monotonic, so NTP/DST wall-clock adjustments can't skew
    # (or negate) the measured duration.
    start_time = time.perf_counter()
    result = executor.sql(sql)
    output = render_result(result, output_format)
    time_str = format_elapsed(time.perf_counter() - start_time)
    return output, time_str
