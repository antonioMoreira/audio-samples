import shutil

import av
import yaml
from typer.testing import CliRunner

from audio_samples.cli import DEFAULT_OUTPUT_DIR, app
from tests.test_converter import _create_synthetic_mp4
from tests.test_utils import _create_synthetic_wav

runner = CliRunner()


def test_cli_requires_config_argument():
    result = runner.invoke(app, [])
    assert result.exit_code != 0


def test_cli_audio_not_found(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
version: 3
audio_path: "samples/nonexistent_audio.wav"
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
    wav_file = _create_synthetic_wav(tmp_path / "sample.wav", duration_sec=60.0)
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(f"""
version: 3
audio_path: "{wav_file}"
sampling_rule: "Random"
chunks:
  - chunk_size_seconds: 5
    amount: -1
""")
    result = runner.invoke(app, [str(bad_yaml)])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr


def test_cli_insufficient_duration(tmp_path):
    wav_file = _create_synthetic_wav(tmp_path / "sample.wav", duration_sec=60.0)
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(f"""
version: 3
audio_path: "{wav_file}"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 10
    amount: 10
""")
    result = runner.invoke(app, [str(bad_yaml)])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr


def test_cli_happy_continuous(tmp_path):
    wav_file = _create_synthetic_wav(tmp_path / "sample.wav", duration_sec=60.0)
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text(f"""
version: 3
audio_path: "{wav_file}"
chunks_dirname: "test_continuous_run"
sampling_rule: "Continuous"
remove_seconds:
  - [10, 20]
chunks:
  - chunk_size_seconds: 15
    amount: 2
""")

    target_dir = DEFAULT_OUTPUT_DIR / "test_continuous_run"
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
    wav_file = _create_synthetic_wav(tmp_path / "sample.wav", duration_sec=60.0)
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text(f"""
version: 3
audio_path: "{wav_file}"
chunks_dirname: "test_random_run"
sampling_rule: "Random"
seed: 42
chunks:
  - chunk_size_seconds: 5
    amount: 2
""")

    target_dir = DEFAULT_OUTPUT_DIR / "test_random_run"
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


def test_cli_relative_audio_path_from_project_root(tmp_path, monkeypatch):
    monkeypatch.setattr("audio_samples.cli.PROJECT_ROOT", tmp_path)

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    _create_synthetic_wav(samples_dir / "rel_sample.wav", duration_sec=10.0)

    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 3
audio_path: "samples/rel_sample.wav"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 2
    amount: 2
""")

    result = runner.invoke(app, [str(rules_yaml)])
    assert result.exit_code == 0

    target_dir = tmp_path / "output" / "rel_sample"
    assert target_dir.exists()
    assert (target_dir / "2" / "0-2.wav").exists()
    assert (target_dir / "2" / "2-4.wav").exists()


def test_cli_custom_output_path(tmp_path, monkeypatch):
    monkeypatch.setattr("audio_samples.cli.PROJECT_ROOT", tmp_path)

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    _create_synthetic_wav(samples_dir / "rel_sample.wav", duration_sec=10.0)

    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 3
audio_path: "samples/rel_sample.wav"
output_path: "samples"
chunks_dirname: "rel_sample-Continuous"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 2
    amount: 2
""")

    result = runner.invoke(app, [str(rules_yaml)])
    assert result.exit_code == 0

    target_dir = tmp_path / "samples" / "rel_sample-Continuous"
    assert target_dir.exists()
    assert (target_dir / "2" / "0-2.wav").exists()
    assert (target_dir / "2" / "2-4.wav").exists()


def test_cli_mp4_not_found(tmp_path):
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 3
audio_path: "samples/nonexistent_video.mp4"
chunks:
  - chunk_size_seconds: 2
    amount: 1
""")
    result = runner.invoke(app, [str(rules_yaml)])
    assert result.exit_code == 1
    assert (
        "Error: Video file not found" in result.stdout
        or "Error: Video file not found" in result.stderr
    )


def test_cli_yaml_with_mp4_normalizes_and_slices(tmp_path):
    video_file = tmp_path / "My Sliced Video (1).mp4"
    _create_synthetic_mp4(
        video_file, include_audio=True, sample_rate=16000, duration_sec=10.0
    )

    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text(f"""
version: 3
audio_path: "{video_file}"
sampling_rule: "Continuous"
chunks:
  - chunk_size_seconds: 2
    amount: 2
""")

    target_dir = DEFAULT_OUTPUT_DIR / "My_Sliced_Video_1"
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
    with av.open(str(wav_file)) as c:
        st = c.streams.audio[0]
        assert st.sample_rate == 16000
        assert st.channels == 1
        assert st.format.name == "s16"

    assert target_dir.exists()
    assert (target_dir / "2").exists()
    chunks = list((target_dir / "2").glob("*.wav"))
    assert len(chunks) == 2
    shutil.rmtree(target_dir)
