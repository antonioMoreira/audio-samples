# YAML v2: YAML-Driven Audio Chunks Slicer

## Problem Statement
Currently, several slicing parameters (e.g., `audio_name`, `chunks_dirname`, `sampling_rule`, `seed`) are provided as command-line arguments and options in `cli.py`. To make execution more reproducible and declarative, we want to transition to a schema where **all** parameters are defined directly inside the configuration YAML file (Version 2). The CLI will accept a single configuration file path, load all parameters from it, and execute.

## Goals
- [ ] Update `RulesConfig` model to support YAML v2 parameters (`audio_name`, `chunks_dirname`, `sampling_rule`, `seed`) with sensible defaults for YAML v1 backward compatibility.
- [ ] Update the CLI signature in `cli.py` to accept only a single `config_path` argument (defaulting to the default rules file).
- [ ] Load and apply all parameters directly from the loaded YAML configuration instead of CLI flags.
- [ ] Ensure that `ty` and `ruff` pass cleanly.
- [ ] Re-implement/update the tests in `tests/` to align with the new YAML-driven architecture.

## Out of Scope
- Support for complex override options on the command line (all configurations should reside in the YAML file).

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| **Default Config Path** | `src/audio_samples/default_rule.yaml` | Retain fallback rules path when no argument is supplied. | y |
| **Default Audio Name** | `"a_ia_ta_ai-1min"` | Specified in the request. | y |
| **Backward Compatibility** | YAML v1 remains parsable by defaulting `audio_name`, `sampling_rule`, etc. in Pydantic. | Prevents breaking v1 files if reused. | y |

---

## User Stories

### P1: YAML-Driven Execution ⭐ MVP
**User Story**: As an ML developer, I want to run the audio slicer by passing a single configuration YAML file so that all execution parameters are kept together in a readable, versionable, and reproducible format.

**Acceptance Criteria**:
1. WHEN the CLI is invoked with a YAML v2 file THEN the system SHALL load `audio_name`, `chunks_dirname`, `sampling_rule`, `seed`, and `chunks` from the YAML and execute slicing accordingly.
2. WHEN the configuration YAML is not provided THEN the system SHALL use `default_rule.yaml` which defaults to version 2 and the default audio file.
3. WHEN the YAML file does not exist THEN the system SHALL raise a clear file-not-found error and exit with status 1.

**Independent Test**:
Run `uv run audio-slicer` (uses default YAML v2) and confirm it slices the default audio file correctly.

---

## Requirement Traceability

| Requirement ID | Story / Feature | Phase | Status |
| --- | --- | --- | --- |
| `YAMLV2-01` | RulesConfig Pydantic model update | Design | Verified |
| `YAMLV2-02` | CLI signature and argument change | Design | Verified |
| `YAMLV2-03` | Parameter extraction from loaded YAML model | Design | Verified |
| `YAMLV2-04` | YAML v2 default config file update | Design | Verified |
| `YAMLV2-05` | Test suite refactoring and verification | Design | Verified |

**Coverage**: 5 total requirements, 5 mapped, 0 unmapped ✨

---

## Success Criteria
- [x] The CLI accepts a single path argument and executes without requiring options like `--sampling-rule` or `--chunks-dirname`.
- [x] `ty check` and `ruff check` pass cleanly on all modified files.
- [x] `pytest` passes with high coverage.
