# Agent Guidelines

- Create scratch/test scripts at `/tmp/` and execute them with `uv run`.
- Do not use `python3 -c` commands.
- Always run `uv run ty` (e.g. `uv run ty check`) and `uv run ruff` (`uv run ruff check` and `uv run ruff format`); any problems or diagnostics reported must be fixed.
