# pksql

Command line SQL on parquet files using DuckDB

## Installation

### For Users

Install directly from GitHub:

```bash
# Using pip
pip install git+https://github.com/dbolser/pksql.git

# Using pip with SSH (if you have SSH keys configured)
pip install git+ssh://git@github.com/dbolser/pksql.git
```

### For Developers

#### Using pip

```bash
pip install -e .
```

#### Using uv

If you prefer using uv:

```bash
uv pip install -e .
```

## Usage

pksql can be used in two ways: direct query mode and interactive mode.

### Direct Query Mode

Run SQL queries directly on Parquet files using DuckDB:

```bash
# Query a single Parquet file
pksql SELECT * FROM 'data.parquet'

# Count rows in multiple Parquet files
pksql SELECT COUNT(*) FROM 'multiple_*.parquet'

# Perform aggregations
pksql SELECT col1, COUNT(*) FROM 'some.parquet' GROUP BY col1
```

### Interactive Mode

Interactive mode provides a shell-like environment where you can run SQL queries without having to quote file paths and escape special characters. This is especially useful for running multiple queries on the same files.

#### Starting Interactive Mode

```bash
# Start the interactive shell
pksql -i

# Start with pre-registered file aliases
pksql -i data.parquet as mydata
pksql -i file1.parquet as data1 file2.parquet as data2

# Using glob patterns
pksql -i "/path/to/*.parquet" as alldata
```

#### Interactive Commands

Once in the interactive shell, you can use the following commands:

```
# Register a file alias
pksql> alias mydata /path/to/data.parquet

# Register a glob pattern as an alias
pksql> alias alldata '/path/to/*.parquet'

# View files that match a glob pattern
pksql> glob /path/to/*.parquet

# List all registered aliases
pksql> aliases

# Remove an alias
pksql> unalias mydata

# Run SQL queries on aliases
pksql> SELECT * FROM mydata
pksql> SELECT COUNT(*) FROM mydata

# Direct queries on files (including glob patterns)
pksql> SELECT * FROM '/path/to/data.parquet'
pksql> SELECT COUNT(*) FROM '/path/to/*.parquet'

# Exit the interactive shell
pksql> exit
pksql> quit
```

#### Working with Glob Patterns

Glob patterns allow you to query multiple files at once:

1. When using glob patterns in the interactive shell:
   ```
   # Register a glob pattern
   pksql> alias mydata '/path/to/*.parquet'
   
   # Or query directly
   pksql> SELECT * FROM '/path/to/*.parquet'
   ```

2. When using glob patterns on the command line:
   ```bash
   # Use quotes to prevent shell expansion
   pksql -i "/path/to/*.parquet" as mydata
   ```

### Important Notes

- In direct query mode, enclose file paths in single quotes to prevent shell glob expansion
- In interactive mode, file paths can be used without quotes when registering aliases
- Use the alias feature to simplify queries and avoid shell parsing issues
- You can use standard SQL syntax supported by DuckDB
- The output uses DuckDB's built-in formatting for readability
- Query execution time is displayed after each query

## Requirements

- Python 3.8+
- DuckDB
- Click
- Rich (for interactive shell formatting)

## Project History

This project started with a simple idea:

> I want a simple 'command line' utility that lets me run DuckDB SQL on a given set of parquet files.

The implementation uses Click for the CLI interface and DuckDB for querying Parquet files directly. The interactive mode was added to make it easier to run queries without having to worry about shell escaping and quoting.

## TODO

● Update Todos
  ⎿  ☒ Add DuckDB and click dependencies
     ☒ Set up project structure for CLI tool
     ☒ Implement CLI interface with query handling
     ☒ Format and display query results
     ☒ Add installation instructions to README
     ☒ Implement interactive mode
     ☒ Add support for file aliases
     ☒ Update README with interactive mode documentation

