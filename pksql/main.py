"""CLI entry point for pksql."""

import sys
import os
import time
import click
import duckdb
from rich.console import Console

console = Console()

@click.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('args', nargs=-1)
@click.option('--interactive', '-i', is_flag=True, help='Start in interactive mode')
@click.option('--output-format', '-F', 'output_format',
              type=click.Choice(['table', 'csv', 'tsv'], case_sensitive=False),
              default='table',
              help='Output format for query results')
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
    # Check if we should enter interactive mode
    if interactive or (len(args) >= 3 and "as" in args):
        from pksql.interactive import start_interactive_shell, PKSQLShell
        
        # Check if we have file aliases to register
        if len(args) >= 3 and "as" in args:
            from pksql.interactive import PKSQLShell
            shell = PKSQLShell()
            
            # Parse file aliases (format: file.parquet as alias)
            i = 0
            while i < len(args):
                # Find the pattern: file_path as alias
                if i + 2 < len(args) and args[i+1].lower() == "as":
                    file_path = args[i]
                    alias = args[i+2]
                    
                    # Register the alias - let the shell handle file existence checks
                    try:
                        shell.do_alias(f"{alias} {file_path}")
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
        full_query = ' '.join(args)
        
        try:
            # Start timing
            start_time = time.time()

            # Use duckdb.sql which provides nice formatting out of the box
            result = duckdb.sql(full_query)

            is_query = full_query.strip().lower().startswith(
                ("select", "show", "describe", "explain")
            )

            if output_format == "table":
                if is_query:
                    # Display results using DuckDB's pretty formatting
                    print(result)
                else:
                    console.print("Query executed successfully.")
            else:
                delimiter = "," if output_format == "csv" else "\t"
                if is_query:
                    header = delimiter.join(result.columns)
                    print(header)
                    for row in result.fetchall():
                        print(delimiter.join(map(str, row)))
                else:
                    console.print("Query executed successfully.")
            
            # End timing and display
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Format query time based on duration
            if elapsed < 0.001:
                time_str = f"{elapsed*1000000:.2f} μs"
            elif elapsed < 1:
                time_str = f"{elapsed*1000:.2f} ms"
            else:
                time_str = f"{elapsed:.3f} sec"
                
            console.print(f"Query time: {time_str}")
            
        except Exception as e:
            console.print(f"Error: {str(e)}")
            sys.exit(1)
    
    else:
        # No arguments and not interactive mode, show help
        ctx = click.get_current_context()
        click.echo(ctx.get_help())

if __name__ == "__main__":
    cli()