"""CLI entry point for pksql."""

import shlex
import sys

import click
from rich.console import Console

from pksql.core import execute_query

console = Console()
conserr = Console(stderr=True)


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
            output, time_str = execute_query(full_query, output_format=output_format)

            if output is not None:
                # Result-producing query: results go to stdout.
                print(output)
            elif output_format != "table":
                # Non-query statement: report success on stderr so structured
                # output on stdout stays clean. (Table mode stays silent, as
                # DuckDB has no table to render.)
                conserr.print("Query executed successfully.")

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
