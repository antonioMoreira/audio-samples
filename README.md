# Audio Chunks Slicer

A robust, type-safe Python Command-Line Interface (CLI) tool designed to slice long WAV audio files into smaller, precise chunks of target durations (e.g., 2s, 10s, 30s). Powered by `PyAV` (FFmpeg Python bindings), `Pydantic` (v2), and `Typer`, this tool is tailored for creating training and evaluation datasets for machine learning audio models.

---

## Features

- 📜 **YAML-Driven Configuration (v2)**: Fully declarative slicing rules. Define inputs, outputs, sampling methods, and segment rules in a single, versionable YAML file.
- 🔀 **Multiple Sampling Modes**:
  - `Continuous`: Slices the audio sequentially from start to end.
  - `Random`: Samples a specified number of non-overlapping, disjoint chunks randomly.
- 🚫 **Skip Intervals (`remove_seconds`)**: Skip unwanted audio intervals (silence, intro/outros, or noise) globally or per-slice rules.
- ⚙️ **Feasibility Check**: Validates and mathematically guarantees that slicing requirements can be satisfied (e.g., sufficient audio length, valid exclusion boundaries) before writing any output files.
- 🔒 **Type-Safe & Quality Checked**: Fully static-typed and validated with `ty` and linted with `ruff`.

---

## Installation & Setup

This repository uses [`uv`](https://github.com/astral-sh/uv) for lightning-fast and reproducible Python package and environment management.

### Prerequisites

Make sure you have Python 3.12+ and `uv` installed. You will also need `ffmpeg` libraries installed on your system for PyAV to bind correctly.

```bash
# Clone the repository
git clone <repo-url>
cd audio-samples

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
uv pip install -e .
```

---

## Usage

You can run the slicer directly via `uv run`:

```bash
# Run using the default configuration (default_rule.yaml)
uv run audio-slicer

# Run specifying a custom configuration file
uv run audio-slicer path/to/config.yaml
```

---

## Configuration Schema (YAML v2)

The tool reads all parameters from a single configuration file. Here is an example of a YAML v2 file:

```yaml
version: 2
audio_name: "a_ia_ta_ai-1min"
chunks_dirname: "a_ia_ta_ai-1min"
sampling_rule: "Continuous"
seed: 42  # Optional: Seed for random placement reproducibility
remove_seconds:
  - [10, 20]  # Global segments to skip/remove
chunks:
  - chunk_size_seconds: 2
    amount: -1  # -1 means slice all available audio sequentially
  - chunk_size_seconds: 10
    amount: 5   # Extract exactly 5 chunks of 10s
```

### Field Definitions

- `version`: Configuration schema version (`2` is standard).
- `audio_name`: The filename of the target audio. Must be located inside the `samples/` directory. (If extension `.wav` is omitted, the CLI automatically falls back to `.wav`).
- `chunks_dirname`: Directory name under `samples/` where outputs will be saved. Defaults to `audio_name` stem.
- `sampling_rule`: Slicing method, either `Continuous` or `Random`.
- `seed`: Integer seed for the random number generator (reproducible `Random` sampling).
- `remove_seconds`: List of `[start, end]` second pairs to completely exclude from slicing.
- `chunks`: List of slicing rules:
  - `chunk_size_seconds`: The duration of each chunk.
  - `amount`: Number of chunks to sample. Use `-1` for all possible continuous chunks.

---

## Directory Structure

Output chunks are saved inside a subfolder under `samples/` corresponding to the slice duration:

```
samples/
├── a_ia_ta_ai-1min.wav         # Source audio file
└── a_ia_ta_ai-1min/            # Output chunks directory
    ├── config.yaml             # Summary run file of executed rules
    ├── 2/                      # 2-second chunks
    │   ├── 0-2.wav
    │   ├── 2-4.wav
    │   └── ...
    └── 10/                     # 10-second chunks
        ├── 20-30.wav
        └── ...
```

---

## Development

### Running Tests

We use `pytest` for unit and integration testing.

```bash
uv run pytest
```

### Static Analysis & Type Checking

To verify code quality and complete type safety, run:

```bash
# Check code style and formatting rules
uv run ruff check src/ tests/

# Check static typing diagnostics with ty
ty check src/ tests/
```
