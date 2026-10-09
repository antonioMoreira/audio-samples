import shutil
from pathlib import Path

import av
import yaml
from typer.testing import CliRunner

from audio_samples.cli import app
from tests.test_converter import _create_synthetic_mp4

runner = CliRunner()


def test_cli_audio_not_found(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
version: 2
audio_name: "nonexistent_audio.wav"
chunks:
  - chunk_size_seconds: 2
    amount: 1
""")
    result = runner.invoke(app, [str(config_yaml)])
    assert result.exit_code == 1
    assert (
        "Error: Audio file not found" in result.stdout
        or "Error: Audio file not found" in result.stderr
    )


def test_cli_yaml_not_found():
    result = runner.invoke(app, ["nonexistent_rules.yaml"])
    assert result.exit_code == 1
    assert (
        "Error: YAML rules file not found" in result.stdout
        or "Error: YAML rules file not found" in result.stderr
    )


def test_cli_malformed_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("chunks:\n  - chunk_size_seconds: -10")
    result = runner.invoke(app, [str(bad_yaml)])
    assert result.exit_code == 1
    assert "Validation Error" in result.stdout or "Validation Error" in result.stderr


def test_cli_random_all_exclusive(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("""
version: 2
audio_name: "a_ia_ta_ai-1min.wav"
sampling_rule: "Random"
chunks:
  - chunk_size_seconds: 5
    amount: -1
""")
    result = runner.invoke(app, [str(bad_yaml)])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr


def test_cli_insufficient_duration(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("""
version: 2
audio_name: "a_ia_ta_ai-1min.wav"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 10
    amount: 10
""")
    result = runner.invoke(app, [str(bad_yaml)])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr


def test_cli_happy_continuous(tmp_path):
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 2
audio_name: "a_ia_ta_ai-1min.wav"
chunks_dirname: "test_continuous_run"
sampling_rule: "Continuous"
remove_seconds:
  - [10, 20]
chunks:
  - chunk_size_seconds: 15
    amount: 2
""")

    target_dir = Path("samples/test_continuous_run")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [str(rules_yaml)])

    assert result.exit_code == 0
    assert "Slicing operation completed successfully" in result.stdout

    assert target_dir.exists()
    assert (target_dir / "config.yaml").exists()

    size_dir = target_dir / "15"
    assert size_dir.exists()
    assert (size_dir / "20-35.wav").exists()
    assert (size_dir / "35-50.wav").exists()

    with open(target_dir / "config.yaml") as f:
        data = yaml.safe_load(f)
        assert data["version"] == 1
        assert data["chunks"] == [{"chunk_size_seconds": 15, "amount": 2}]

    shutil.rmtree(target_dir)


def test_cli_happy_random(tmp_path):
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 2
audio_name: "a_ia_ta_ai-1min.wav"
chunks_dirname: "test_random_run"
sampling_rule: "Random"
seed: 42
chunks:
  - chunk_size_seconds: 5
    amount: 2
""")

    target_dir = Path("samples/test_random_run")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [str(rules_yaml)])

    assert result.exit_code == 0
    assert "Slicing operation completed successfully" in result.stdout

    assert target_dir.exists()
    assert (target_dir / "config.yaml").exists()

    size_dir = target_dir / "5"
    assert size_dir.exists()

    files = list(size_dir.glob("*.wav"))
    assert len(files) == 2

    with open(target_dir / "config.yaml") as f:
        data = yaml.safe_load(f)
        assert data["version"] == 1
        assert data["chunks"] == [{"chunk_size_seconds": 5, "amount": 2}]

    shutil.rmtree(target_dir)


def test_cli_mp4_not_found():
    result = runner.invoke(app, ["nonexistent_video.mp4"])
    assert result.exit_code == 1
    assert (
        "Error: Video file not found" in result.stdout
        or "Error: Video file not found" in result.stderr
    )


def test_cli_direct_mp4_arg_normalizes_and_slices(tmp_path):
    video_file = tmp_path / "This is a video.mp4"
    _create_synthetic_mp4(
        video_file, include_audio=True, sample_rate=16000, duration_sec=32.0
    )

    target_dir = Path("samples/This_is_a_video")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [str(video_file)])
    assert result.exit_code == 0
    assert "Slicing operation completed successfully" in result.stdout

    # Original file should have been renamed on disk to normalized name
    normalized_video = tmp_path / "This_is_a_video.mp4"
    assert normalized_video.exists()
    assert not video_file.exists()

    # WAV file should exist and have 16000 Hz mono properties
    wav_file = tmp_path / "This_is_a_video.wav"
    assert wav_file.exists()
    with av.open(str(wav_file)) as c:
        st = c.streams.audio[0]
        assert st.sample_rate == 16000
        assert st.channels == 1
        assert st.format.name == "s16"

    assert target_dir.exists()
    assert (target_dir / "config.yaml").exists()
    assert (target_dir / "2").exists()
    assert (target_dir / "10").exists()
    assert (target_dir / "30").exists()
    shutil.rmtree(target_dir)


def test_cli_yaml_with_mp4_normalizes_and_slices(tmp_path):
    video_file = tmp_path / "My Sliced Video (1).mp4"
    _create_synthetic_mp4(
        video_file, include_audio=True, sample_rate=16000, duration_sec=10.0
    )

    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text(f"""
version: 2
audio_name: "{video_file}"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 2
    amount: 2
""")

    target_dir = Path("samples/My_Sliced_Video_1")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [str(rules_yaml)])
    assert result.exit_code == 0
    assert "Slicing operation completed successfully" in result.stdout

    normalized_video = tmp_path / "My_Sliced_Video_1.mp4"
    assert normalized_video.exists()
    assert not video_file.exists()

    wav_file = tmp_path / "My_Sliced_Video_1.wav"
    assert wav_file.exists()

    assert target_dir.exists()
    assert (target_dir / "2").exists()
    chunks = list((target_dir / "2").glob("*.wav"))
    assert len(chunks) == 2
    shutil.rmtree(target_dir)
