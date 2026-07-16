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

### AD-006
- **Decision**: Transition to YAML v2 configurations where all execution parameters (`audio_name`, `chunks_dirname`, `sampling_rule`, `seed`) are declared in the YAML config instead of CLI options.
- **Reason**: Simplifies invocation, improves reproducibility, and unifies configuration.
- **Trade-off**: Requires changing CLI signature and updating tests.
- **Scope**: CLI invocation and configuration schema.
- **Date**: 2026-07-14
- **Status**: active

### AD-007
- **Decision**: Add wav2base64 utility script and pyperclip dependency to support fast, reliable WAV-to-base64 conversion.
- **Reason**: Requested by the user to facilitate base64 asset encoding.
- **Trade-off**: Introduces pyperclip dependency.
- **Scope**: wav2base64 feature.
- **Date**: 2026-07-15
- **Status**: active

## Handoff

- **Feature**: wav2base64
- **Phase / Task**: Execute / Completed and verified
- **Completed**: Specification, Design, Implementation, and Verification (.specs/features/wav2base64/spec.md)
- **In-progress**: none
- **Next step**: Propose features, close tickets
- **Blockers**: none
- **Uncommitted files**: none (all changes committed or verified)
- **Branch**: main



