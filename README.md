# Audio Chunks Slicer

A robust, type-safe Python Command-Line Interface (CLI) tool designed to slice long WAV audio files into smaller, precise chunks of target durations (e.g., 2s, 10s, 30s). Powered by `PyAV` (FFmpeg Python bindings), `Pydantic` (v2), and `Typer`, this tool is tailored for creating training and evaluation datasets for machine learning audio models.

---

## Features

- 🎥 **MP4 Video Ingestion & Conversion**: Specify `.mp4` video files or `.wav` audio files via `audio_path` in your configuration. Converts video audio to 16 kHz mono WAV using `PyAV` (equivalent to `ffmpeg -i [VIDEO].mp4 -ar 16000 -ac 1 [VIDEO].wav`).
- 🏷️ **Automatic Name Normalization**: Cleans and normalizes filenames containing spaces or special characters on disk (e.g., `"This is a video.mp4"` $\rightarrow$ `"This_is_a_video.mp4"`).
- 📜 **YAML-Driven Configuration (v3)**: Fully declarative slicing rules. Define inputs, outputs, sampling methods, and segment rules in a single, versionable YAML file.
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

You can run the slicer directly via `uv run` by providing a configuration YAML file:

```bash
# Run specifying a configuration file (required)
uv run audio-slicer samples/continuous.yaml
uv run audio-slicer samples/random.yaml
```

---

## Configuration Schema (YAML v3)

The tool reads all parameters from a single configuration file. Here is an example of a YAML v3 file:

```yaml
version: 3
audio_path: "samples/a_ia_ta_ai_slice_90-255.wav"
output_path: "output"  # Optional: defaults to "output"
chunks_dirname: "a_ia_ta_ai_slice_90-255-Continuous"
sampling_rule: "Continuous"
seed: 42  # Optional: Seed for random placement reproducibility
remove_seconds:
  - [10, 20]  # Global segments to skip/remove
chunks:
  - chunk_size_seconds: 10
    amount: 10
  - chunk_size_seconds: 20
    amount: 5
  - chunk_size_seconds: 30
    amount: -1  # -1 means slice all available audio sequentially
```

### Field Definitions

- `version`: Configuration schema version (`3` is required).
- `audio_path`: Path to the target audio (`.wav`) or video (`.mp4`) file, including the file extension. If not absolute, it is resolved relative to the project root.
- `output_path`: Base output directory path. Defaults to `"output"`. If not absolute, it is resolved relative to the project root.
- `chunks_dirname`: Directory name under `output_path` where outputs will be saved. Defaults to `audio_path` stem.
- `sampling_rule`: Slicing method, either `Continuous` or `Random`.
- `seed`: Integer seed for the random number generator (reproducible `Random` sampling).
- `remove_seconds`: List of `[start, end]` second pairs to completely exclude from slicing.
- `chunks`: List of slicing rules:
  - `chunk_size_seconds`: The duration of each chunk.
  - `amount`: Number of chunks to sample. Use `-1` for all possible continuous chunks.

---

## Directory Structure

Output chunks are saved inside a subfolder under `output/` corresponding to `chunks_dirname` and the slice duration:

```
output/
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
uv run ty check src/ tests/
```
