"""Interactive shell for pksql."""

import cmd
import glob
import os

import duckdb
from rich.console import Console

from pksql.core import execute_query

console = Console()
conserr = Console(stderr=True)


class PKSQLShell(cmd.Cmd):
    """Interactive shell for running SQL queries on Parquet files."""

    intro = """
Welcome to pksql interactive shell!
Type help or ? for help.
Type exit or quit to exit.
    """
    prompt = "pksql> "

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = duckdb.connect(database=":memory:")
        self.file_aliases = {}

    def default(self, line):
        """Handle SQL queries by default."""
        try:
            output, time_str = execute_query(line, conn=self.conn)

            if output is not None:
                print(output)
            else:
                console.print("Query executed successfully.")

            conserr.print(f"Query time: {time_str}")
        except Exception as e:
            console.print(f"Error: {str(e)}")

    def do_alias(self, arg):
        """Register a Parquet file or glob pattern with an alias.

        Usage: alias <alias_name> <file_path_or_glob>

        Examples:
          alias data /path/to/data.parquet
          alias alldata '/path/to/*.parquet'
        """
        parts = arg.strip().split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[bold red]Error:[/bold red] alias requires both an alias name and a file path."
            )
            return

        alias_name = parts[0]
        # Strip matching outer quotes to support both quoted and unquoted paths
        raw_path = parts[1]
        if (
            len(raw_path) >= 2
            and raw_path[0] == raw_path[-1]
            and raw_path[0] in ("'", '"')
        ):
            file_path = raw_path[1:-1]
        else:
            file_path = raw_path

        # Verify the path exists (for specific files) or has matches (for glob
        # patterns). DuckDB binds the view at CREATE time, so an empty local
        # glob can't be deferred — warn and bail out rather than register an
        # alias whose view creation is about to fail.
        if "://" in file_path:
            # Remote path (s3://, https://, ...). DuckDB/httpfs resolves these;
            # local globbing can't validate them, so skip the check.
            pass
        elif any(ch in file_path for ch in "*?["):
            expanded = os.path.expanduser(os.path.expandvars(file_path))
            if not glob.glob(expanded, recursive=True):
                console.print(
                    f"Warning: No files currently match pattern: {file_path}"
                )
                console.print("Alias not registered.")
                return
        elif not os.path.exists(os.path.expanduser(os.path.expandvars(file_path))):
            console.print(f"Warning: File not found: {file_path}")
            console.print("If this is a glob pattern, enclose it in single quotes.")

        # Create the view first; only record the alias if it succeeds, so a
        # failed CREATE never leaves a half-registered alias in `aliases`.
        try:
            # Use single quotes around the file path to ensure proper handling by DuckDB
            quoted_path = f"'{file_path}'"
            self.conn.sql(
                f"CREATE OR REPLACE VIEW {alias_name} AS SELECT * FROM {quoted_path}"
            )
            self.file_aliases[alias_name] = file_path
            console.print(f"Alias {alias_name} registered for {file_path}")
        except Exception as e:
            console.print(f"Error: Failed to create view: {str(e)}")

    def do_aliases(self, arg):
        """List all registered file aliases."""
        if not self.file_aliases:
            console.print("No aliases registered.")
            return

        console.print("Registered aliases:")
        for alias, path in self.file_aliases.items():
            console.print(f"{alias} -> {path}")

    def do_unalias(self, arg):
        """Remove a registered alias.

        Usage: unalias <alias_name>
        """
        alias_name = arg.strip()
        if not alias_name:
            console.print("Error: unalias requires an alias name.")
            return

        if alias_name in self.file_aliases:
            del self.file_aliases[alias_name]
            try:
                self.conn.sql(f"DROP VIEW IF EXISTS {alias_name}")
                console.print(f"Alias {alias_name} removed.")
            except Exception as e:
                console.print(f"Error: Failed to drop view: {str(e)}")
        else:
            console.print(f"Error: Alias {alias_name} not found.")

    def do_glob(self, arg):
        """Display files that match a glob pattern.

        Usage: glob <pattern>

        Example: glob /path/to/*.parquet
        """
        if not arg:
            console.print("Error: glob requires a pattern.")
            return

        pattern = arg.strip().strip("'\"")
        try:
            matches = glob.glob(pattern)
            if matches:
                console.print(f"Found {len(matches)} files matching pattern:")
                for file in matches[
                    :10
                ]:  # Show only first 10 to avoid flooding the terminal
                    console.print(f"  {file}")
                if len(matches) > 10:
                    console.print(f"  ... and {len(matches) - 10} more files")
            else:
                console.print(f"No files found matching pattern: {pattern}")
        except Exception as e:
            console.print(f"Error: {str(e)}")

    def do_exit(self, arg):
        """Exit the interactive shell."""
        # Release the DuckDB connection so long-running sessions don't leak it.
        try:
            self.conn.close()
        except Exception:
            pass  # Connection may already be closed.
        console.print("Goodbye!")
        return True

    def do_quit(self, arg):
        """Exit the interactive shell."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Exit on end-of-file (Ctrl-D)."""
        print()  # Move off the prompt line that Ctrl-D leaves behind.
        return self.do_exit(arg)

    def emptyline(self):
        """Do nothing on empty line."""
        return False

    def do_help(self, arg):
        """Show help for commands."""
        if arg:
            # Show help for a specific command
            super().do_help(arg)
        else:
            # Show general help
            console.print("\nAvailable commands:")
            console.print(
                "  alias <name> <file_path_or_glob> - Register a file or glob with an alias"
            )
            console.print("  aliases - List all registered aliases")
            console.print("  unalias <name> - Remove a registered alias")
            console.print("  glob <pattern> - Display files matching a glob pattern")
            console.print("  exit or quit - Exit the interactive shell")
            console.print("  help or ? - Show this help message")
            console.print("\nSQL statements:")
            console.print("  You can run any SQL statement directly, e.g.:")
            console.print("  SELECT * FROM 'data.parquet' (direct file reference)")
            console.print("  SELECT * FROM '*.parquet' (glob pattern)")
            console.print("  SELECT * FROM my_alias (using registered alias)")
            console.print("\nGlob Pattern Tips:")
            console.print(
                "  - For glob patterns, enclose the pattern in quotes in SQL queries"
            )
            console.print("  - Example: SELECT * FROM '*.parquet'")
            console.print("  - Example: alias mydata '/path/to/*.parquet'")


def start_interactive_shell():
    """Start the interactive shell."""
    shell = PKSQLShell()
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
    finally:
        # Close the connection on every exit route (exit/quit, Ctrl-D, Ctrl-C).
        try:
            shell.conn.close()
        except Exception:
            pass
