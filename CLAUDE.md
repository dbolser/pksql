# CLAUDE.md

Use uv to manage dependencies, e.g. `uv run pytest`.



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