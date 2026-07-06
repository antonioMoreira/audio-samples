# Audio Chunks Slicer Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Spec**: `.specs/features/audio_slicer/spec.md`
**Context**: `.specs/features/audio_slicer/context.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec — confirm before Execute. Guidelines found: none — strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain | unit | All layout/logic functions, math checks, edge cases, 1:1 to spec ACs | `tests/test_*.py` | `uv run pytest` |
| CLI | integration | Happy path runs, missing files, invalid YAML configurations | `tests/test_cli.py` | `uv run pytest` |

## Parallelism Assessment

> Generated from codebase — confirm before Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit | Yes | Isolated test functions using unique temp directories or mocked file handles | No shared database or global state in Python's standard `pytest` |
| integration | Yes | Executing CLI runs targeting unique output folder paths under temp directory | Subprocess or direct CLI calls run isolated |

## Gate Check Commands

> Generated from codebase — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `uv run pytest` |
| Full | After tasks with integration tests | `uv run pytest` |
| Build | After phase completion or config-only tasks | `uv run ruff check src/ && uv run pytest` |

---

## Execution Plan

### Phase 1: Foundation (Sequential)

Setting up dependencies and core configuration models.

```
T1 ──→ T2 ──→ T3
└──────→ T4
```

### Phase 2: Core Slicing Layouts (Parallel OK)

Mathematical validation and layouts generation for Continuous and Random sampling.

```
           ┌→ T5 [P]
T3, T4 ───┤
           └→ T6 [P]
```

### Phase 3: Slicing & Integration (Sequential)

Slicing execution using PyAV and CLI wiring using Typer.

```
T5, T6, T4 ──→ T7 ──→ T8
```

---

## Task Breakdown

### T1: Project Dependency Setup
**What**: Add project dependencies `typer`, `pydantic`, `av`, `pyyaml`, `ruff`, and `pytest` using `uv`.
**Where**: `pyproject.toml`
**Depends on**: None
**Reuses**: none
**Requirement**: `SLICER-01`, `SLICER-02`, `SLICER-10`

**Tools**:
- MCP: `filesystem`
- Skill: `managing-python-dependencies`

**Done when**:
- [x] Dependencies added to `pyproject.toml` and verified installed.
- [x] `uv run ruff --version` and `uv run pytest --version` run successfully.

**Tests**: none
**Gate**: build

---

### T2: Create Pydantic Rule Models & YAML Parser
**What**: Define Pydantic models for configuration `ChunksRule` and YAML rule parser that reads yaml to models.
**Where**: `src/audio_samples/rules.py`
**Depends on**: T1
**Reuses**: none
**Requirement**: `SLICER-02`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [x] `ChunksRule` Pydantic model defined with fields `chunk_size_seconds`, `amount`, and `remove_seconds`.
- [x] YAML parser function loads yaml config into a list of validated `ChunksRule`.
- [x] Unit tests verify loading valid rules, invalid rules (e.g. negative chunk sizes), and default yaml.

**Tests**: unit
**Gate**: quick

---

### T3: Implement Feasibility & Constraints Verification
**What**: Implement the math helper to verify if the audio duration and constraints can fit the requested chunk rules.
**Where**: `src/audio_samples/feasibility.py`
**Depends on**: T2
**Reuses**: none
**Requirement**: `SLICER-04`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [x] Function implemented to calculate the total available duration after removing `remove_seconds` intervals.
- [x] Function verifies that `amount` is specified (> 0) if `sampling_rule` is `Random`.
- [x] Checks that total requested duration (sum of chunk size * amount) does not exceed total available duration.
- [x] Unit tests cover various feasibility scenarios, both passing and failing with descriptive errors.

**Tests**: unit
**Gate**: quick

---

### T4: PyAV Audio Properties Loader
**What**: Implement a function using PyAV to read audio metadata, specifically total duration and sample rate.
**Where**: `src/audio_samples/loader.py`
**Depends on**: T1
**Reuses**: none
**Requirement**: `SLICER-03`, `SLICER-05`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [x] PyAV audio properties loader implemented.
- [x] Returns correct duration as integer/float.
- [x] Unit tests verify metadata reading using a mock or a small test WAV file.

**Tests**: unit
**Gate**: quick

---

### T5: Continuous Layout Generator [P]
**What**: Implement sequential chunk boundaries generator obeying `remove_seconds`.
**Where**: `src/audio_samples/layout_continuous.py`
**Depends on**: T3, T4
**Reuses**: none
**Requirement**: `SLICER-06`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [x] Function returns sequential `(start_seconds, end_seconds)` chunks from beginning of file.
- [x] Skipped segments perfectly respect `remove_seconds`.
- [x] Unit tests verify sequential output, correct skipping of blocked intervals, and handling of `amount = -1`.

**Tests**: unit
**Gate**: quick

---

### T6: Random Disjoint Layout Generator [P]
**What**: Implement random chunk boundaries generator satisfying disjointness constraints.
**Where**: `src/audio_samples/layout_random.py`
**Depends on**: T3, T4
**Reuses**: none
**Requirement**: `SLICER-07`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [x] Function returns randomized `(start_seconds, end_seconds)` chunks that are completely disjoint.
- [x] Validates mutually exclusive `amount = -1` constraint for `Random`.
- [x] Implements 1000 retry limit, raising a descriptive error on failure.
- [x] Unit tests verify disjointness, random selection, and retry error trigger.

**Tests**: unit
**Gate**: quick

---

### T7: PyAV Slicing Writer
**What**: Implement precise audio slice writer that reads audio segment and saves it as a new WAV file.
**Where**: `src/audio_samples/writer.py`
**Depends on**: T4
**Reuses**: none
**Requirement**: `SLICER-05`, `SLICER-08`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [ ] Slice function extracts precise audio from `start` to `end` second using PyAV.
- [ ] Writes correct formatted WAV file to target directory.
- [ ] Unit tests verify slice accuracy with a small generated audio file.

**Tests**: unit
**Gate**: quick

---

### T8: Typer CLI and Output Config Integration
**What**: Implement CLI command using Typer, integrate the validation/layout/slicing, and generate output config YAML.
**Where**: `src/audio_samples/cli.py`, `src/audio_samples/__main__.py`
**Depends on**: T2, T5, T6, T7
**Reuses**: none
**Requirement**: `SLICER-01`, `SLICER-08`, `SLICER-09`

**Tools**:
- MCP: `filesystem`
- Skill: none

**Done when**:
- [ ] Typer CLI parses arguments: `audio_name`, `chunks_dirname`, `chunks_rules_yaml`, `sampling_rule`.
- [ ] CLI correctly runs validations, layouts, slices, and writes files in target subdirectories.
- [ ] Existing output subdirectories are safely cleared before running.
- [ ] Writes `config.yaml` detailing actual generated chunks.
- [ ] Integration tests verify complete E2E run on sample audios, yielding correct layout and config files.

**Tests**: integration
**Gate**: full

---

## Parallel Execution Map

Visual representation of task ordering:

```
Phase 1 (Sequential):
  T1 ──→ T2 ──→ T3
  T1 ──→ T4

Phase 2 (Parallel):
  T3 and T4 complete, then:
    ├── T5 [P]
    └── T6 [P]

Phase 3 (Sequential):
  T5 and T6 complete, then:
    T7 ──→ T8
```

**Parallelism constraint**: Tasks `T5` and `T6` are marked `[P]` because they are purely functional, have no shared state, and can run in any order.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Dependency Setup | 1 file change | ✅ Granular |
| T2: Rules Model | 1 file, 1 concept | ✅ Granular |
| T3: Feasibility check | 1 function | ✅ Granular |
| T4: Audio properties loader | 1 function | ✅ Granular |
| T5: Continuous layout | 1 function | ✅ Granular |
| T6: Random layout | 1 function | ✅ Granular |
| T7: Slicing writer | 1 function | ✅ Granular |
| T8: CLI integration | 1 entrypoint file | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 ──→ T2 | ✅ Match |
| T3 | T2 | T2 ──→ T3 | ✅ Match |
| T4 | T1 | T1 ──→ T4 | ✅ Match |
| T5 | T3, T4 | T3, T4 ──→ T5 | ✅ Match |
| T6 | T3, T4 | T3, T4 ──→ T6 | ✅ Match |
| T7 | T4 | T4 ──→ T7 | ✅ Match |
| T8 | T2, T5, T6, T7 | T5, T6, T7 ──→ T8 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | config | none | none | ✅ OK |
| T2 | Domain | unit | unit | ✅ OK |
| T3 | Domain | unit | unit | ✅ OK |
| T4 | Domain | unit | unit | ✅ OK |
| T5 | Domain | unit | unit | ✅ OK |
| T6 | Domain | unit | unit | ✅ OK |
| T7 | Domain | unit | unit | ✅ OK |
| T8 | CLI | integration | integration | ✅ OK |
