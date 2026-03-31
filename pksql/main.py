"""CLI entry point for pksql."""

import json
import os
import shlex
import sys
import time
from datetime import date, datetime
from datetime import time as time_type
from decimal import Decimal

import click
import duckdb
from rich.console import Console

console = Console()
conserr = Console(stderr=True)


def json_serializer(obj):
    """Custom JSON serializer for non-serializable objects."""
    if isinstance(obj, (datetime, date, time_type)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        # Convert binary data to base64 string
        import base64

        return base64.b64encode(obj).decode("utf-8")
    else:
        # Fallback for any other non-serializable types
        return str(obj)


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("args", nargs=-1)
@click.option("--interactive", "-i", is_flag=True, help="Start in interactive mode")
@click.option(
    "--output-format",
    "-F",
    "output_format",
    type=click.Choice(["table", "csv", "tsv", "json"], case_sensitive=False),
    default="table",
    help="Output format for query results",
)
def cli(args, interactive, output_format):
    """Run SQL queries on Parquet files using DuckDB.

    There are two main ways to use pksql:

    1. Direct query mode:
       pksql SELECT * FROM 'file.parquet'

    2. Interactive mode with file aliases:
       pksql -i
       pksql -i file.parquet as mydata

    Examples:
        pksql SELECT * FROM 'file.parquet'
        pksql SELECT COUNT(*) FROM 'multiple_*.parquet'
        pksql SELECT col1, COUNT(*) FROM 'some.parquet' GROUP BY col1
        pksql -i
        pksql -i data.parquet as mydata
    """
    parsed_args = list(args)

    # Check if we should enter interactive mode
    if interactive or (len(parsed_args) >= 3 and "as" in parsed_args):
        from pksql.interactive import PKSQLShell, start_interactive_shell

        # Check if we have file aliases to register
        if len(parsed_args) >= 3 and "as" in parsed_args:
            shell = PKSQLShell()

            # Parse file aliases (format: file.parquet as alias)
            i = 0
            while i < len(parsed_args):
                # Find the pattern: file_path as alias
                if i + 2 < len(parsed_args) and parsed_args[i + 1].lower() == "as":
                    file_path = parsed_args[i]
                    alias = parsed_args[i + 2]

                    # Register the alias - let the shell handle file existence checks
                    try:
                        shell.do_alias(f"{alias} {shlex.quote(file_path)}")
                    except Exception as e:
                        console.print(f"Error: Failed to register alias: {str(e)}")

                    i += 3
                else:
                    i += 1

            shell.cmdloop()
        else:
            # Start the interactive shell with no pre-registered aliases
            start_interactive_shell()

    # If not interactive, treat args as a SQL query
    elif args:
        # Join all arguments as they form the SQL query
        full_query = " ".join(args)

        try:
            # Start timing
            start_time = time.time()

            # Use duckdb.sql which provides nice formatting out of the box
            result = duckdb.sql(full_query)

            # Determine if this is a query that returns results by checking the result object
            is_query = (
                result is not None
                and hasattr(result, "columns")
                and bool(result.columns)
            )

            if output_format == "table":
                if is_query:
                    # Display results using DuckDB's pretty formatting
                    print(result)
            elif output_format in ("csv", "tsv"):
                delimiter = "," if output_format == "csv" else "\t"
                if is_query:
                    header = delimiter.join(result.columns)
                    print(header)
                    for row in result.fetchall():
                        print(delimiter.join(map(str, row)))
                else:
                    conserr.print("Query executed successfully.")
            elif output_format == "json":
                if is_query:
                    rows = [dict(zip(result.columns, row)) for row in result.fetchall()]
                    print(json.dumps(rows, default=json_serializer))
                else:
                    conserr.print("Query executed successfully.")

            # End timing and display
            end_time = time.time()
            elapsed = end_time - start_time

            # Format query time based on duration
            if elapsed < 0.001:
                time_str = f"{elapsed * 1000000:.2f} μs"
            elif elapsed < 1:
                time_str = f"{elapsed * 1000:.2f} ms"
            else:
                time_str = f"{elapsed:.3f} sec"

            conserr.print(f"Query time: {time_str}")

        except Exception as e:
            console.print(f"Error: {str(e)}")
            sys.exit(1)

    else:
        # No arguments and not interactive mode, show help
        ctx = click.get_current_context()
        click.echo(ctx.get_help())


if __name__ == "__main__":
    cli()
