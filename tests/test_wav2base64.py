import base64
import sys
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.wav2base64 import app

runner = CliRunner()


def test_convert_success_default(tmp_path):
    # Create a small dummy file
    wav_file = tmp_path / "test.wav"
    data = b"RIFFfakeWAVdata"
    wav_file.write_bytes(data)

    expected_base64 = base64.b64encode(data).decode("utf-8")

    # Patch pyperclip.copy so it doesn't interact with the system clipboard
    with patch("pyperclip.copy") as mock_copy:
        result = runner.invoke(app, ["convert", str(wav_file)])

        assert result.exit_code == 0
        mock_copy.assert_called_once_with(expected_base64)
        assert result.stdout == ""  # No output to stdout by default


def test_convert_success_with_print(tmp_path):
    wav_file = tmp_path / "test.wav"
    data = b"RIFFfakeWAVdata"
    wav_file.write_bytes(data)

    expected_base64 = base64.b64encode(data).decode("utf-8")

    with patch("pyperclip.copy") as mock_copy:
        result = runner.invoke(
            app, ["convert", str(wav_file), "--print"]
        )

        assert result.exit_code == 0
        mock_copy.assert_called_once_with(expected_base64)
        assert expected_base64 in result.stdout.strip()


def test_convert_success_no_clipboard(tmp_path):
    wav_file = tmp_path / "test.wav"
    data = b"RIFFfakeWAVdata"
    wav_file.write_bytes(data)

    with patch("pyperclip.copy") as mock_copy:
        result = runner.invoke(
            app, ["convert", str(wav_file), "--no-clipboard", "--print"]
        )

        assert result.exit_code == 0
        mock_copy.assert_not_called()
        assert base64.b64encode(data).decode("utf-8") in result.stdout.strip()


def test_convert_file_not_found():
    result = runner.invoke(app, ["convert", "nonexistent.wav"])
    assert result.exit_code == 1
    assert (
        "Error: File not found" in result.stdout
        or "Error: File not found" in result.stderr
    )


def test_convert_is_directory(tmp_path):
    result = runner.invoke(app, ["convert", str(tmp_path)])
    assert result.exit_code == 1
    assert (
        "Error: Path is a directory" in result.stdout
        or "Error: Path is a directory" in result.stderr
    )
