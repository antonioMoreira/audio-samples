# STATE

## Decisions

### AD-001
- **Decision**: Use only `uv` to manage python dependencies, run scripts, and create virtual environments.
- **Reason**: Defined in docs/first_spec.md as a project constraint.
- **Trade-off**: Restricts the use of raw pip/poetry.
- **Scope**: Entire project dependency management.
- **Date**: 2026-07-06
- **Status**: active

### AD-002
- **Decision**: Use `pydantic` for data validation, configuration parsing, and internal data structures.
- **Reason**: Specified in docs/first_spec.md.
- **Trade-off**: Adds a runtime dependency on Pydantic.
- **Scope**: Data validation.
- **Date**: 2026-07-06
- **Status**: active

### AD-003
- **Decision**: Use `ruff` for linting and static type/style checking.
- **Reason**: Specified in docs/first_spec.md.
- **Trade-off**: Standardizes code formatting and quality checks.
- **Scope**: Linting and formatting.
- **Date**: 2026-07-06
- **Status**: active

### AD-004
- **Decision**: Use `typer` for building the command-line interface.
- **Reason**: Specified in docs/first_spec.md.
- **Trade-off**: Standardizes CLI parsing and user interactions.
- **Scope**: CLI entry point.
- **Date**: 2026-07-06
- **Status**: active

### AD-005
- **Decision**: Use `PyAV` for all audio loading, decoding, and slicing operations.
- **Reason**: Specified in docs/first_spec.md.
- **Trade-off**: Requires binary C-bindings for ffmpeg, but offers frame-precise slicing and decodes faster than pure python.
- **Scope**: Audio processing engine.
- **Date**: 2026-07-06
- **Status**: active

## Handoff

- **Feature**: audio_slicer
- **Phase / Task**: Specify / Create initial specification from docs/first_spec.md
- **Completed**: none
- **In-progress**: .specs/features/audio_slicer/spec.md
- **Next step**: Propose the initial specification to the user and request feedback / discussion of gray areas.
- **Blockers**: none
- **Uncommitted files**: .specs/STATE.md
- **Branch**: main
