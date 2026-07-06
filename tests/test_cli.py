import shutil
from pathlib import Path
import pytest
import yaml
from typer.testing import CliRunner
from audio_samples.cli import app

runner = CliRunner()

def test_cli_audio_not_found():
    result = runner.invoke(app, ["nonexistent_audio.wav"])
    assert result.exit_code == 1
    assert "Error: Audio file not found" in result.stdout or "Error: Audio file not found" in result.stderr

def test_cli_yaml_not_found():
    result = runner.invoke(app, ["a_ia_ta_ai-1min.wav", "--chunks-rules-yaml", "nonexistent_rules.yaml"])
    assert result.exit_code == 1
    assert "Error: YAML rules file not found" in result.stdout or "Error: YAML rules file not found" in result.stderr

def test_cli_malformed_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("chunks:\n  - chunk_size_seconds: -10")
    result = runner.invoke(app, ["a_ia_ta_ai-1min.wav", "--chunks-rules-yaml", str(bad_yaml)])
    assert result.exit_code == 1
    assert "Validation Error" in result.stdout or "Validation Error" in result.stderr

def test_cli_random_all_exclusive(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("version: 1\nchunks:\n  - chunk_size_seconds: 5\n    amount: -1")
    result = runner.invoke(app, [
        "a_ia_ta_ai-1min.wav",
        "--chunks-rules-yaml", str(bad_yaml),
        "--sampling-rule", "Random"
    ])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr

def test_cli_insufficient_duration(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("version: 1\nchunks:\n  - chunk_size_seconds: 10\n    amount: 10")
    result = runner.invoke(app, [
        "a_ia_ta_ai-1min.wav",
        "--chunks-rules-yaml", str(bad_yaml),
        "--sampling-rule", "Continuous"
    ])
    assert result.exit_code == 1
    assert "Feasibility Error" in result.stdout or "Feasibility Error" in result.stderr

def test_cli_happy_continuous(tmp_path):
    rules_yaml = tmp_path / "rules.yaml"
    rules_yaml.write_text("""
version: 1
remove_seconds:
  - [10, 20]
chunks:
  - chunk_size_seconds: 15
    amount: 2
""")

    target_dir = Path("samples/test_continuous_run")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [
        "a_ia_ta_ai-1min.wav",
        "--chunks-dirname", "test_continuous_run",
        "--chunks-rules-yaml", str(rules_yaml),
        "--sampling-rule", "Continuous"
    ])

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
version: 1
chunks:
  - chunk_size_seconds: 5
    amount: 2
""")

    target_dir = Path("samples/test_random_run")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    result = runner.invoke(app, [
        "a_ia_ta_ai-1min.wav",
        "--chunks-dirname", "test_random_run",
        "--chunks-rules-yaml", str(rules_yaml),
        "--sampling-rule", "Random",
        "--seed", "42"
    ])

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
