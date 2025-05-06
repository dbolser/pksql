"""Interactive shell for pksql."""

import cmd
import duckdb
import glob
import os
import sys
import time
from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax

console = Console()

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
            # Start timing
            start_time = time.time()
            
            if line.lower().startswith(("select", "show", "describe", "explain")):
                result = self.conn.sql(line)
                print(result)
            else:
                self.conn.sql(line)
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
    
    def do_alias(self, arg):
        """Register a Parquet file or glob pattern with an alias.
        
        Usage: alias <alias_name> <file_path_or_glob>
        
        Examples: 
          alias data /path/to/data.parquet
          alias alldata '/path/to/*.parquet'
        """
        args = arg.strip().split(maxsplit=1)
        if len(args) < 2:
            console.print("[bold red]Error:[/bold red] alias requires both an alias name and a file path.")
            return
            
        alias_name = args[0]
        file_path = args[1]
        
        # Remove quotes if present
        file_path = file_path.strip("'\"")
        
        # Verify the path exists (for specific files) or has matches (for glob patterns)
        if '*' in file_path or '?' in file_path:
            # This is a glob pattern
            # Let DuckDB handle it directly without checking first
            pass
        elif not os.path.exists(file_path):
            console.print(f"Warning: File not found: {file_path}")
            console.print("If this is a glob pattern, enclose it in single quotes.")
            
        # Register the alias
        self.file_aliases[alias_name] = file_path
        
        # Create a view for the file or glob pattern
        try:
            # Use single quotes around the file path to ensure proper handling by DuckDB
            quoted_path = f"'{file_path}'"
            self.conn.sql(f"CREATE OR REPLACE VIEW {alias_name} AS SELECT * FROM {quoted_path}")
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
                for file in matches[:10]:  # Show only first 10 to avoid flooding the terminal
                    console.print(f"  {file}")
                if len(matches) > 10:
                    console.print(f"  ... and {len(matches) - 10} more files")
            else:
                console.print(f"No files found matching pattern: {pattern}")
        except Exception as e:
            console.print(f"Error: {str(e)}")
    
    def do_exit(self, arg):
        """Exit the interactive shell."""
        console.print("Goodbye!")
        return True
        
    def do_quit(self, arg):
        """Exit the interactive shell."""
        return self.do_exit(arg)
        
    def emptyline(self):
        """Do nothing on empty line."""
        pass
        
    def do_help(self, arg):
        """Show help for commands."""
        if arg:
            # Show help for a specific command
            super().do_help(arg)
        else:
            # Show general help
            console.print("\nAvailable commands:")
            console.print("  alias <name> <file_path_or_glob> - Register a file or glob with an alias")
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
            console.print("  - For glob patterns, enclose the pattern in quotes in SQL queries")
            console.print("  - Example: SELECT * FROM '*.parquet'")
            console.print("  - Example: alias mydata '/path/to/*.parquet'")
            
def start_interactive_shell():
    """Start the interactive shell."""
    shell = PKSQLShell()
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
        sys.exit(0)