# CLAUDE.md

Use uv to manage dependencies, e.g. `uv run pytest`.

## Layout

- `pksql/main.py` — the Click CLI. A `QueryGroup` dispatches an unrecognised
  first argument to the `query` subcommand, so `pksql "SELECT 1"` and
  `pksql add-alias ...` can share one entry point.
- `pksql/aliases.py` — reading, writing and binding `.pksql` alias files.
- `pksql/core.py` — running a statement, rendering it for an output format and
  timing it. Kept apart from the CLI so "did this produce a result set?" is
  decided in one place.

## Key Design Patterns

1. **One-shot only**: every invocation runs a single query and exits. There is
   no REPL — an earlier interactive shell was removed because aliases
   registered in it died with the session.

2. **Alias files**: `~/.pksql` then `./.pksql`, both `name = path` lines, local
   winning on a name clash. Relative paths resolve against the directory of the
   file that declared them, so a `.pksql` survives being moved with its project.

3. **Aliases become views**: each alias is a `CREATE OR REPLACE VIEW <name> AS
   SELECT * FROM '<path>'` on a fresh in-memory connection. DuckDB binds the
   path at CREATE time, so `create_views` swallows failures — otherwise one
   stale entry would break every query. A dead alias then surfaces only when a
   query names it, as DuckDB's own "does not exist" error.

4. **Alias names are identifiers**: they are interpolated straight into SQL, so
   `NAME_RE` restricts them rather than trying to escape arbitrary text. Paths
   are single-quoted with `'` doubled.

   `add-alias` additionally runs `is_usable_name`, which asks DuckDB by
   attempting `CREATE VIEW <name> AS SELECT 1`. Do not swap this for a keyword
   list: `keyword_category = 'reserved'` covers only 75 of the 105 words DuckDB
   rejects unquoted — 30 `type_function` words (`anti`, `asof`, `at`, `by`, ...)
   fail too, and the set moves between releases.

5. **Mutations parse before they write**: `update_file` reads the whole file
   first, so `add-alias` cannot report success on a file that every later
   command will choke on.

6. **Streams**: results on stdout, timing and errors on stderr, so `-F json |
   jq` stays clean.

## Entry Point Configuration

```toml
[project.scripts]
pksql = "pksql.main:cli"
```

## Dependencies

- **duckdb**: SQL engine
- **click**: CLI framework
- **rich**: terminal formatting

## CLI Surface

- `pksql "<sql>"` — run a query (`-F table|csv|tsv|json`)
- `pksql add-alias <name> [=] <path>` — register an alias (`-g` for `~/.pksql`)
- `pksql aliases` — list aliases and their source files
- `pksql rm-alias <name>` — remove an alias (`-g` for `~/.pksql`)

## Testing

`tests/conftest.py` provides a `workspace` fixture giving each test an empty
working directory and its own `$HOME`. Any test that touches alias lookup must
use it, or it will read the developer's real `~/.pksql`.

Note that Click 8.2's `result.output` is the *combined* stream; assert against
`result.stdout` / `result.stderr` when the distinction matters.
