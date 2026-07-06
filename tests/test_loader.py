import pytest
from pathlib import Path
from audio_samples.loader import load_audio_properties


def test_load_audio_properties_real_file():
    # Use the real 1-minute file available in the samples/ directory
    path = Path("samples/a_ia_ta_ai-1min.wav")
    assert path.exists(), f"{path} must exist in the workspace to run tests"

    duration, sample_rate = load_audio_properties(path)
    assert pytest.approx(duration, 0.01) == 60.0
    assert sample_rate == 16000


def test_load_audio_properties_file_not_found():
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        load_audio_properties("non_existent_file_xyz.wav")


def test_load_audio_properties_invalid_file(tmp_path):
    # Write some garbage to a temp file and try to load it
    invalid_file = tmp_path / "garbage.wav"
    invalid_file.write_text("not a real wav file")
    with pytest.raises(ValueError, match="Could not open audio file"):
        load_audio_properties(invalid_file)
