# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pksql is a command-line SQL tool for querying Parquet files using DuckDB. It supports both direct query mode and an interactive shell with file aliasing capabilities.

## Development Commands

### Installation and Setup
```bash
# Install in development mode using pip
pip install -e .

# Or using uv (preferred)
uv pip install -e .
```

### Running the Tool
```bash
# Direct query mode
pksql SELECT * FROM 'file.parquet'

# Interactive mode
pksql -i

# Interactive mode with pre-registered aliases
pksql -i data.parquet as mydata
```

## Architecture

### Core Components

- **pksql/main.py**: CLI entry point using Click framework. Handles argument parsing and delegates to either direct query execution or interactive mode.
- **pksql/interactive.py**: Interactive shell implementation using Python's `cmd` module. Provides SQL REPL with file aliasing, glob pattern support, and DuckDB integration.

### Key Design Patterns

1. **Dual Mode Operation**: The tool operates in two distinct modes:
   - Direct query mode: Execute single SQL queries from command line
   - Interactive mode: REPL shell with persistent state and file aliases

2. **File Aliasing System**: Interactive mode creates DuckDB views for registered file aliases, allowing users to reference complex file paths or glob patterns with simple names.

3. **Glob Pattern Handling**: Both modes support glob patterns for querying multiple Parquet files simultaneously. Interactive mode provides `glob` command to preview matching files.

4. **Rich Output**: Uses Rich library for formatted console output and timing information.

### Entry Point Configuration

The CLI entry point is configured in pyproject.toml as:
```toml
[project.scripts]
pksql = "pksql.main:cli"
```

### Dependencies

- **duckdb**: Core SQL engine for Parquet file queries
- **click**: Command-line interface framework
- **rich**: Terminal formatting and output enhancement

## Interactive Shell Commands

- `alias <name> <path>`: Register file or glob pattern with alias
- `aliases`: List all registered aliases  
- `unalias <name>`: Remove alias
- `glob <pattern>`: Preview files matching glob pattern
- `exit`/`quit`: Exit shell

SQL queries are executed directly in the shell prompt without special commands.