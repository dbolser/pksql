# pksql

Command line SQL on parquet files using DuckDB.

pksql runs a DuckDB query from your shell and prints the result. Aliases let you
give a long path a short name once, in a `.pksql` file, instead of retyping it.

## Installation

```bash
uv pip install pksql
# or
pip install pksql
```

Needs Python 3.10+. That is all — DuckDB, Click and Rich come with it.

To work on pksql instead:

```bash
git clone https://github.com/dbolser/pksql.git
cd pksql
uv sync
uv run pytest
```

## Usage

```bash
# Query a single file
pksql "SELECT * FROM 'data.parquet'"

# Query many at once
pksql "SELECT COUNT(*) FROM 'multiple_*.parquet'"

# CSVs work the same way
pksql "SELECT * FROM 'data.csv'"
```

Quote the query. Otherwise your shell expands `*` before pksql sees it.

A `.duckdb` file can be read the same way, but only if it holds exactly one
table — otherwise DuckDB says `Database "corpus.duckdb" has multiple tables`.
For those, attach it and name the table:

```bash
pksql "SELECT * FROM 'corpus.duckdb'"
pksql "ATTACH 'corpus.duckdb' AS c; SELECT * FROM c.documents"
```

### Aliases

Give a path a name, and use that name as a table:

```bash
pksql add-alias corpus = data/s3-backup-20260731/karl/corpus.duckdb
pksql "SELECT * FROM corpus"
```

`add-alias` writes to `.pksql` in the current directory. The `=` is optional, so
`pksql add-alias corpus data/corpus.duckdb` does the same thing.

```bash
# A glob works too - quote it so the shell leaves it alone
pksql add-alias hits 'results/*.parquet'

# Forget the quotes and your shell expands it first; pksql says so
#   Warning: that is 3 files, not one path - your shell expanded the glob.

# Available everywhere, not just this directory
pksql add-alias --global scratch ~/scratch.duckdb

# What's registered, and where from
pksql aliases

# Forget one
pksql rm-alias corpus
```

### The .pksql file

It is a plain list of `name = path` lines, so you can edit it by hand:

```text
# Karl's backup, 2026-07-31
corpus = data/s3-backup-20260731/karl/corpus.duckdb
hits   = 'results/*.parquet'
```

- `~/.pksql` applies everywhere; `./.pksql` adds to it and wins on a name clash.
- Relative paths are read relative to the `.pksql` file, not to where you are.
- An alias pointing at something that isn't there is ignored, so an unplugged
  drive breaks only the queries that actually name it. `pksql aliases` marks
  those `(missing)`.
- An alias named after a DuckDB keyword works, but the query has to quote it:
  `pksql 'SELECT * FROM "select"'`. `add-alias` says so when you register one.

### Output formats

`--output-format` (`-F`) takes `table` (default), `csv`, `tsv` or `json`:

```bash
pksql -F json "SELECT * FROM corpus" | jq .
```

Results go to stdout; the query time and any errors go to stderr, so piping
stays clean.

## Project History

This project started with a simple idea:

> I want a simple 'command line' utility that lets me run DuckDB SQL on a given
> set of parquet files.

It briefly grew an interactive REPL. That turned out to be the wrong shape — the
aliases you set up there died with the session, so they were never worth
registering. Persisting them to a `.pksql` file gave the one-shot CLI the same
convenience, and the REPL was dropped.

## Releasing

Publishing is automatic. Cutting a GitHub release uploads to PyPI; there is no
API token anywhere, because both indexes use trusted publishing (OIDC) — GitHub
mints a short-lived token that the index exchanges for upload rights.

1. Bump `version` in `pyproject.toml` and `__version__` in `pksql/__init__.py`.
   They must match.
2. Merge that to `main`.
3. Optional rehearsal: run the **Publish** workflow manually from the Actions
   tab. A manual run only ever reaches TestPyPI, never PyPI.
4. `gh release create vX.Y.Z --target main --generate-notes`

The release event builds with `uv build`, checks the metadata with
`twine check`, and uploads. Watch it with `gh run watch`.

A few things worth knowing:

- A version number on PyPI is permanent. It can be yanked, never reused. Get the
  bump right before you tag.
- The workflow file is read from the tagged commit, so the tag has to include
  any workflow change you are relying on.
- Publisher registration lives on the index, not here: PyPI uses the `pypi`
  environment, TestPyPI uses `testpypi`, both pinned to `publish.yml`.

## TODO

- [ ] Add schema inspection commands
- [ ] Support for saving query results to files
