# wav2base64 Feature Specification

## Problem Statement
We need a simple, reliable command-line tool to convert WAV audio files into standard base64 strings. To facilitate easy integration with frontend/mock datasets, the tool should easily copy the output directly to the clipboard or optionally print it to standard output.

## Goals
- [ ] Create a script `wav2base64.py` using `typer` that exposes a `convert` command.
- [ ] Implement reading of WAV files and robust conversion to base64 encoding.
- [ ] Add option `--clipboard` (default `True`) using `pyperclip` to copy the base64 string to the system clipboard.
- [ ] Add option `--print` (default `False`) to print the base64 string to stdout.
- [ ] Verify everything using `ruff` and `ty`.
- [ ] Create tests at `tests/`.

## Out of Scope
- Slicing or editing the WAV files before conversion (this script focuses purely on file-to-base64 conversion).
- Conversion of other audio formats (focused on WAV).

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| **Input validation** | Validate that file exists and is a WAV file (ends with .wav). | Prevents attempting to decode directory or non-audio files. | y |
| **Clipboard Support** | Use `pyperclip` to copy to clipboard. | Standard Python cross-platform clipboard library. | y |

---

## User Stories

### P1: wav2base64 Conversion Utility ⭐ MVP
**User Story**: As a developer, I want to convert a WAV file to a base64 string and copy it to my clipboard automatically, so that I can easily paste it into my configuration or code.

**Acceptance Criteria**:
1. WHEN the command `convert` is run with a valid WAV file THEN the system SHALL read the file, encode its binary contents to a base64 ASCII string, and copy it to the clipboard by default.
2. WHEN `--print=True` is specified THEN the system SHALL also output the base64 string to stdout.
3. WHEN the input WAV file does not exist THEN the system SHALL raise a clear file-not-found error and exit with status 1.

**Independent Test**:
Create a dummy WAV file, convert it, and verify that the clipboard contents match the expected base64 encoding.

---

## Requirement Traceability

| Requirement ID | Story / Feature | Phase | Status |
| --- | --- | --- | --- |
| `W2B64-01` | Typer CLI convert command & signature | Design | Verified |
| `W2B64-02` | WAV file binary read and base64 conversion | Design | Verified |
| `W2B64-03` | Clipboard output integration via pyperclip | Design | Verified |
| `W2B64-04` | Stdout printing option integration | Design | Verified |
| `W2B64-05` | Input file existence validation | Design | Verified |
| `W2B64-06` | Test suite implementation and verification | Design | Verified |

**Coverage**: 6 total requirements, 6 mapped, 0 unmapped ✨

---

## Success Criteria
- [x] Running `uv run wav2base64.py convert` with a WAV file copies its base64 content to the clipboard.
- [x] Passing `--print=True` successfully prints the string to stdout.
- [x] `pytest`, `ruff check`, and `ty check` pass on all newly added files.

