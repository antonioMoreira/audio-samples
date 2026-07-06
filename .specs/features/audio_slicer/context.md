# Audio Chunks Slicer Context

**Gathered:** 2026-07-06
**Spec:** `.specs/features/audio_slicer/spec.md`
**Status:** Ready for design

---

## Feature Boundary

A CLI tool that takes an audio file inside `samples/` and slices it into disjoint WAV chunks based on rules specified in a YAML file, following either `Continuous` or `Random` sampling rules, while respecting a `remove_seconds` exclusion list.

---

## Implementation Decisions

### Random Sampling Overlap Failure Handling
- **Decision**: If disjoint random placement cannot be satisfied after 1000 attempts, raise a clear error and abort.
- **Rationale**: Ensures strict disjointness for machine learning validation and training sets.

### Existing Output Directory Handling
- **Decision**: Safely clear and overwrite the existing chunks subdirectory (e.g., `samples/[audio_name]/[chunk_size_seconds]/`) to ensure a clean run.
- **Rationale**: Avoids polluting the outputs of a fresh run with stale chunks from previous configurations.

### Chunk Filename and Time Boundaries Precision
- **Decision**: Use strictly integer seconds for chunk filenames (e.g., `10-20.wav`) and slice bounds.
- **Rationale**: Matches the YAML configuration rules structure and ensures clean and simple file naming.

### Agent's Discretion
- **Logging**: The agent can choose the logging/output formatting style (e.g., standard console prints, rich styling, or simple progress/status updates).
- **Audio Processing Internals**: The choice of precise PyAV frame-seeking versus packet-seeking or container-seeking methods is up to the agent, as long as it achieves the requested integer-precision sliced output WAV files.

### Declined / Undiscussed Gray Areas → Assumptions
- **None**: All identified gray areas were fully discussed and resolved.

---

## Specific References
- No specific references; open to standard Typer, Pydantic, and PyAV patterns.

---

## Deferred Ideas
- **None**: Discussion stayed entirely within the feature scope.
