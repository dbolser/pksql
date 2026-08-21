"""Persistent file aliases, stored in ``.pksql`` files.

A ``.pksql`` file is a list of ``name = path`` lines (``#`` starts a comment)::

    corpus = data/s3-backup-20260731/karl/corpus.duckdb
    hits   = 'results/*.parquet'

``~/.pksql`` supplies aliases everywhere; a ``.pksql`` in the working directory
adds to it and wins on a name collision.  Relative paths are resolved against
the directory holding the file that declared them, so a ``.pksql`` stays
correct wherever the project is checked out.
"""

import glob
import os
import re
from pathlib import Path

import duckdb

ALIAS_FILE = ".pksql"

# Alias names become DuckDB view names and are interpolated straight into SQL,
# so restrict them to plain identifiers rather than trying to escape anything.
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class AliasError(Exception):
    """Raised for a malformed alias name or ``.pksql`` file."""


def global_file():
    """Path of the user-wide alias file."""
    return Path.home() / ALIAS_FILE


def local_file(cwd=None):
    """Path of the working directory's alias file."""
    return (Path.cwd() if cwd is None else Path(cwd)) / ALIAS_FILE


def source_files(cwd=None):
    """Alias files to read, lowest precedence first, skipping any duplicate.

    Running in ``$HOME`` makes the local and global files the same file; it
    should still only be read once.
    """
    files, seen = [], set()
    for path in (global_file(), local_file(cwd)):
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            files.append(path)
    return files


def _strip_quotes(value):
    """Drop one layer of matching outer quotes, if present."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _entry_name(line):
    """The alias a line defines, or ``None`` for blanks and comments."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    name, sep, _ = stripped.partition("=")
    return name.strip() if sep else None


def parse(text, source=ALIAS_FILE):
    """Parse alias-file ``text`` into a ``{name: path}`` dict."""
    aliases = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, sep, path = stripped.partition("=")
        where = f"{source}:{lineno}"
        if not sep:
            raise AliasError(f"{where}: expected 'name = path', got {stripped!r}")
        name, path = name.strip(), _strip_quotes(path.strip())
        if not NAME_RE.match(name):
            raise AliasError(f"{where}: {name!r} is not a valid alias name")
        if not path:
            raise AliasError(f"{where}: alias {name!r} has no path")
        aliases[name] = path
    return aliases


def read_file(path):
    """Parse a single alias file, treating a missing file as empty."""
    path = Path(path)
    try:
        text = path.read_text()
    except FileNotFoundError:
        return {}
    return parse(text, source=str(path))


def resolve(path, relative_to):
    """Expand ``path`` and anchor it to the alias file that declared it."""
    expanded = os.path.expanduser(os.path.expandvars(path))
    if "://" in expanded or os.path.isabs(expanded):
        return expanded
    return os.path.join(str(relative_to), expanded)


def load(cwd=None):
    """Merge every alias file into ``{name: resolved path}``."""
    aliases = {}
    for source in source_files(cwd):
        directory = source.parent
        for name, path in read_file(source).items():
            aliases[name] = resolve(path, directory)
    return aliases


def update_file(path, name, new_path):
    """Set ``name`` to ``new_path`` in ``path``, or remove it if ``new_path`` is None.

    Only the matching line is touched, so hand-written comments and ordering
    survive.  Returns the path ``name`` used to point at, or ``None`` if it was
    not previously set.
    """
    path = Path(path)
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        lines = []

    previous, slot, kept = None, None, []
    for line in lines:
        if _entry_name(line) != name:
            kept.append(line)
            continue
        if previous is None:
            # Reserve this line's position, so a rewrite lands where the alias
            # already was.  Any duplicate definitions collapse into it.
            previous = parse(line, source=str(path))[name]
            slot = len(kept)
            kept.append(None)

    if new_path is None:
        if slot is not None:
            del kept[slot]
    else:
        if slot is None:
            slot = len(kept)
            kept.append(None)
        kept[slot] = f"{name} = {new_path}"

    path.write_text("".join(f"{line}\n" for line in kept))
    return previous


def create_views(conn, aliases):
    """Create a view per alias, skipping any whose path will not bind.

    DuckDB resolves the path at ``CREATE VIEW`` time, so one stale entry would
    otherwise break every query.  Skipping means a dead alias only surfaces
    when a query actually names it, as DuckDB's own "does not exist" error.
    Returns the names that failed.
    """
    failed = []
    for name, path in aliases.items():
        quoted = path.replace("'", "''")
        try:
            conn.sql(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM '{quoted}'")
        except duckdb.Error:
            failed.append(name)
    return failed


def missing(path):
    """Whether a local path currently matches nothing.

    Remote paths are reported as present: only DuckDB can resolve those, and
    checking would cost a network round trip.
    """
    if "://" in path:
        return False
    if any(ch in path for ch in "*?["):
        return not glob.glob(path, recursive=True)
    return not os.path.exists(path)
