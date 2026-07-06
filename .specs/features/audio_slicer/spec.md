# Audio Chunks Slicer Specification

## Problem Statement

To train and evaluate audio machine learning models, developers often need to segment long audio files into smaller, manageable chunks of specific durations (e.g., 2s, 10s, 30s). This project aims to build a robust, type-safe Command-Line Interface (CLI) tool using `typer`, `pydantic`, and `PyAV` to slice WAV audio files from the `samples` directory into disjoint chunks based on structured YAML rules.

## Goals

- [ ] Provide a type-safe CLI to slice audio files with continuous or random sampling configurations.
- [ ] Implement robust YAML configuration parsing using `pydantic` to validate slicing rules.
- [ ] Ensure that chunks are saved with accurate naming formats (`start_seconds-end_seconds.wav`) inside properly structured subdirectories based on chunk sizes.
- [ ] Correctly enforce `remove_seconds` constraints, skipping specified periods of time.
- [ ] Enforce disjointness in `Random` sampling and handle continuous sequential slicing.
- [ ] Run a feasibility check before processing to ensure constraints can be satisfied.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Slicing non-WAV formats | The target output formats and inputs are focused on WAV for simplicity and consistency. |
| Overlapping chunks | By definition, all chunks within a run must be mutually disjoint to avoid data leakage in ML sets. |
| Real-time audio streaming | This is a batch-processing file utility, not a live streaming server. |
| In-place audio modification | Original audio files must remain untouched; chunks are saved in separate subdirectories. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| **Audio Location** | Audios must be located inside the `samples/` directory relative to the repository root. | Specified in `first_spec.md`. | y |
| **Default Chunks Directory** | `samples/[chunks_dirname]/` where `chunks_dirname` defaults to `audio_name` (no extension). | Matches the directory structure shown in the specification. | y |
| **Random Sampling Seed** | Seed the random number generator if a specific flag is passed or use system time by default. | Ensures reproducibility for machine learning experiments. | y |
| **Precision of Slice boundaries** | Strictly integer seconds (e.g., 10-20.wav). | Simplifies slice names and matches the YAML structure. | y |
| **Continuous Sampling start** | Begins at 0 seconds (or the first valid second after `remove_seconds`). | Standard sequential slicing starts at the beginning of the file. | y |

---

## User Stories

### P1: CLI Setup and Rule Parsing ⭐ MVP
**User Story**: As an ML developer, I want to run a CLI tool with an audio filename and a rules YAML file so that I can configure my slicing parameters without modifying any code.
**Why P1**: This is the core entry point for the entire application.

**Acceptance Criteria**:
1. WHEN the CLI is invoked with an `audio_name` that does not exist in `samples/` THEN the system SHALL raise a clear error and exit with status 1.
2. WHEN the CLI is invoked with a malformed YAML rule file THEN the system SHALL validate it using a `pydantic` model (`ChunksRule`) and raise a validation error.
3. WHEN `sampling_rule` is `Random` and `amount = -1` for any rule THEN the system SHALL fail validation before processing, since `Random` sampling requires a finite number of chunks.

**Independent Test**:
Can run `uv run audio-slicer nonexistent.wav` and get a clear file-not-found error.

---

### P1: Continuous Slicing with Removed Periods ⭐ MVP
**User Story**: As an ML developer, I want to slice my audio file sequentially while skipping unwanted segments (e.g. silence, noise, or intro/outro) so that I only get high-quality sequential chunks.
**Why P1**: Crucial for generating clean sequential datasets.

**Acceptance Criteria**:
1. WHEN `sampling_rule` is `Continuous` and `remove_seconds` is provided THEN the system SHALL place chunks sequentially, completely skipping any intervals that overlap with `remove_seconds`.
2. WHEN `amount = -1` and `sampling_rule` is `Continuous` THEN the system SHALL slice the entire audio from start to finish (excluding removed intervals) into chunks of `chunk_size_seconds`.
3. WHEN a chunk size is larger than an available continuous segment (due to `remove_seconds` or audio end) THEN that segment SHALL be skipped, and the next valid starting position found.

**Independent Test**:
Given a 60s audio and rule `remove_seconds: [(10, 20)]` and `chunk_size_seconds: 15`, verify that chunks are created at `20-35.wav`, `35-50.wav`, `50-65.wav` (if duration is enough), skipping the `0-10` segment (too short for 15s) and `10-20` (removed).

---

### P1: Random Disjoint Slicing ⭐ MVP
**User Story**: As an ML developer, I want to sample a specified number of chunks randomly from the audio file so that my dataset is diverse and does not contain overlapping audio snippets.
**Why P1**: Disjoint random sampling is a fundamental requirement for unbiased ML validation sets.

**Acceptance Criteria**:
1. WHEN `sampling_rule` is `Random` THEN the system SHALL randomly select start times for the specified `amount` of chunks.
2. WHEN random chunk start times are selected THEN every chosen chunk SHALL be completely disjoint from all other chosen chunks across all sizes, and must not overlap with `remove_seconds`.
3. WHEN the random sampler cannot find disjoint intervals after 1000 placement attempts THEN the system SHALL raise a clear error.

**Independent Test**:
Given `samples_agro1.wav`, run random sampling with size 10s and amount 2, and verify that the two resulting wav chunks do not overlap with each other and are exactly 10s long.

---

### P2: Feasibility & Constraints Verification
**User Story**: As a developer, I want the tool to quickly check if my slicing constraints can be mathematically satisfied before actually writing files, so I don't waste time or get partial outputs.
**Why P2**: Avoids partial pipeline runs and corruption.

**Acceptance Criteria**:
1. WHEN a slicing run starts THEN the system SHALL compute the total available valid audio duration (total duration minus the sum of removed/overlapping intervals).
2. WHEN the required total chunk duration (sum of `amount * chunk_size_seconds` for all rules with `amount > 0`) exceeds the available valid audio duration THEN the system SHALL abort immediately and print a descriptive error.
3. WHEN `Continuous` mode is used and the sequential layout of chunks cannot fit the requested `amount` THEN the system SHALL abort.

**Independent Test**:
Run with a 10s audio requesting 5 chunks of 3s, verify it aborts with a descriptive message (needs 15s, only 10s available).

---

### P2: Outputs and Directory Structure
**User Story**: As a data engineer, I want the generated chunks to be saved in structured folders and a summary YAML file written, so that my downstream loader can easily find them.
**Why P2**: Standardizes data formatting for loaders.

**Acceptance Criteria**:
1. WHEN chunks are successfully written THEN they SHALL be placed in `samples/[chunks_dirname]/[chunk_size_seconds]/[start_seconds]-[end_seconds].wav`.
2. WHEN a slicing operation completes THEN a `config.yaml` file (representing the actual generated chunks and rules) SHALL be written to `samples/[chunks_dirname]/config.yaml`.
3. WHEN the target output directory already contains files THEN the system SHALL clear them or safely recreate the directory to ensure clean runs.

**Independent Test**:
Verify folder structure after running `samples_agro1.yaml` matches the spec tree exactly.

---

## Edge Cases

- **Extremely Short Audio**: Audio file is shorter than the requested `chunk_size_seconds` -> SHALL abort with descriptive error.
- **Overlapping/Redundant `remove_seconds`**: E.g. `[(0, 20), (10, 30)]` -> SHALL normalize to a single interval `[(0, 30)]` before performing feasibility checks and sampling.
- **Floating Point Precision**: PyAV duration might have minor floating point discrepancies -> SHALL handle audio boundaries with safe tolerance (e.g. 0.01 seconds).
- **Exact fit**: Total duration matches exactly `amount * chunk_size_seconds` -> SHALL succeed and place chunks.

---

## Requirement Traceability

| Requirement ID | Story / Feature | Phase | Status |
| --- | --- | --- | --- |
| `SLICER-01` | CLI Setup (Typer) | Design | Pending |
| `SLICER-02` | Rule parsing and Pydantic validation | Design | Pending |
| `SLICER-03` | Input audio file validation | Design | Pending |
| `SLICER-04` | Feasibility check & math validations | Design | Pending |
| `SLICER-05` | PyAV Audio Slicing Engine | Design | Pending |
| `SLICER-06` | Continuous Slicing Algorithm | Design | Pending |
| `SLICER-07` | Random Disjoint Slicing Algorithm | Design | Pending |
| `SLICER-08` | Output layout & File naming format | Design | Pending |
| `SLICER-09` | Output config.yaml creation | Design | Pending |
| `SLICER-10` | Unit & Integration testing suite | Design | Pending |

**Coverage**: 10 total requirements, 0 mapped to tasks, 10 unmapped ⚠️

---

## Success Criteria

- [ ] Successful slicing of any valid WAV file into continuous chunks matching `amount` and `chunk_size_seconds`.
- [ ] Complete assurance of disjointness: no two random chunks share any overlapping second of audio.
- [ ] Strict compliance with `remove_seconds` constraints.
- [ ] Full test coverage (>90% statement coverage on slicing logic).
