"""CLI entry point for pksql."""

import contextlib
import sys

import click
import duckdb
from rich.console import Console

from pksql import aliases as alias_store
from pksql.core import execute_query

# Long file paths read better unbroken than wrapped mid-token.
console = Console(soft_wrap=True)
conserr = Console(stderr=True, soft_wrap=True)


@contextlib.contextmanager
def reporting_alias_errors():
    """Report a malformed ``.pksql`` as an error rather than a traceback."""
    try:
        yield
    except alias_store.AliasError as e:
        conserr.print(f"Error: {e}")
        sys.exit(1)


class QueryGroup(click.Group):
    """A group that treats an unrecognised first argument as a SQL query.

    Running a query is the common case, so it should not have to be spelled
    out: ``pksql "SELECT 1"`` and ``pksql add-alias ...`` both work.
    """

    def resolve_command(self, ctx, args):
        if args and args[0] not in self.commands:
            command = self.get_command(ctx, "query")
            return command.name, command, args
        return super().resolve_command(ctx, args)


@click.group(
    cls=QueryGroup,
    # Bare `pksql` shows help and succeeds; a group would otherwise treat the
    # missing subcommand as a usage error.
    invoke_without_command=True,
    no_args_is_help=False,
    # Options belong to the subcommand, so let unknown ones through untouched
    # rather than rejecting `pksql -F json "SELECT 1"` before dispatch.
    context_settings=dict(ignore_unknown_options=True),
)
@click.pass_context
def cli(ctx):
    """Run DuckDB SQL over Parquet, CSV and DuckDB files.

    \b
    Examples:
        pksql "SELECT * FROM 'data.parquet'"
        pksql "SELECT COUNT(*) FROM 'multiple_*.parquet'"
        pksql -F json "SELECT 1 AS a"

    \b
    Aliases save you retyping long paths.  They live in ./.pksql (or ~/.pksql
    with --global) and are available to every query run from that directory:
        pksql add-alias corpus = data/s3-backup-20260731/karl/corpus.duckdb
        pksql "SELECT * FROM corpus"
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("sql", nargs=-1, required=True)
@click.option(
    "--output-format",
    "-F",
    "output_format",
    type=click.Choice(["table", "csv", "tsv", "json"], case_sensitive=False),
    default="table",
    help="Output format for query results",
)
def query(sql, output_format):
    """Run a SQL query (assumed when no subcommand is given)."""
    with reporting_alias_errors():
        registered = alias_store.load()

    conn = duckdb.connect(database=":memory:")
    try:
        alias_store.create_views(conn, registered)
        try:
            output, time_str = execute_query(
                " ".join(sql), conn=conn, output_format=output_format
            )
        except Exception as e:
            conserr.print(f"Error: {str(e)}")
            sys.exit(1)

        if output is not None:
            # Result-producing query: results go to stdout.
            print(output)
        elif output_format != "table":
            # Non-query statement: report success on stderr so structured
            # output on stdout stays clean. (Table mode stays silent, as
            # DuckDB has no table to render.)
            conserr.print("Query executed successfully.")

        conserr.print(f"Query time: {time_str}")
    finally:
        conn.close()


def _split_assignment(words):
    """Split ``add-alias`` arguments into ``(name, path)``.

    ``corpus path``, ``corpus = path`` and ``corpus=path`` are all accepted:
    the ``=`` is optional sugar, so only the leading tokens are searched for
    it and a path may contain one.
    """
    name, sep, path = words[0].partition("=")
    rest = list(words[1:])
    if not sep and rest and rest[0].startswith("="):
        path = rest.pop(0)[1:]
    # Join rather than require quoting, so paths containing spaces just work.
    return name.strip(), " ".join(part for part in [path, *rest] if part).strip()


def _target_file(use_global):
    return alias_store.global_file() if use_global else alias_store.local_file()


@cli.command("add-alias")
@click.argument("words", nargs=-1, required=True)
@click.option(
    "--global",
    "-g",
    "use_global",
    is_flag=True,
    help="Write to ~/.pksql instead of ./.pksql",
)
def add_alias(words, use_global):
    """Point an alias at a file, glob or URL.

    \b
        pksql add-alias corpus = data/corpus.duckdb
        pksql add-alias hits 'results/*.parquet'
    """
    name, path = _split_assignment(words)
    if not alias_store.NAME_RE.match(name):
        conserr.print(f"Error: {name!r} is not a valid alias name.")
        sys.exit(1)
    if not path:
        conserr.print(f"Error: no path given for alias {name!r}.")
        sys.exit(1)

    target = _target_file(use_global)
    with reporting_alias_errors():
        previous = alias_store.update_file(target, name, path)
    if previous is not None and previous != path:
        console.print(f"{name} = {path} [dim](was {previous})[/dim]")
    else:
        console.print(f"{name} = {path}")
    if alias_store.needs_quoting(name):
        # The bare SQL parser error would not mention the alias, so say it here.
        conserr.print(
            f"Note: {name} is a DuckDB keyword, so queries must quote it: "
            f'SELECT * FROM "{name}"'
        )
    if alias_store.missing(alias_store.resolve(path, target.parent)):
        conserr.print(
            f"Warning: nothing matches {path} yet "
            "(quote globs so the shell cannot expand them)."
        )


@cli.command("rm-alias")
@click.argument("name")
@click.option(
    "--global",
    "-g",
    "use_global",
    is_flag=True,
    help="Remove from ~/.pksql instead of ./.pksql",
)
def rm_alias(name, use_global):
    """Remove an alias."""
    target = _target_file(use_global)
    with reporting_alias_errors():
        removed = alias_store.update_file(target, name, None)
    if removed is None:
        conserr.print(f"Error: alias {name!r} is not in {target}.")
        sys.exit(1)
    console.print(f"Removed {name}.")


@cli.command("aliases")
def list_aliases():
    """List the aliases available here, and where they come from."""
    with reporting_alias_errors():
        sources = [
            (source, alias_store.read_file(source))
            for source in alias_store.source_files()
        ]

    if not any(entries for _, entries in sources):
        console.print("No aliases registered. Try: pksql add-alias name = path")
        return

    for source, entries in sources:
        if not entries:
            continue
        console.print(f"[bold]{source}[/bold]")
        width = max(len(name) for name in entries)
        for name, path in entries.items():
            note = (
                " [yellow](missing)[/yellow]"
                if alias_store.missing(alias_store.resolve(path, source.parent))
                else ""
            )
            console.print(f"  {name:<{width}} = {path}{note}")


if __name__ == "__main__":
    cli()
