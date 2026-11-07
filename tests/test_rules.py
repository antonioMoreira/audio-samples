import pytest
from pydantic import ValidationError

from audio_samples.rules import ChunksRule, load_rules_from_yaml


def test_valid_chunks_rule_defaults():
    # Test valid configuration with defaults
    rule = ChunksRule(chunk_size_seconds=10)
    assert rule.chunk_size_seconds == 10
    assert rule.amount == -1
    assert rule.remove_seconds is None


def test_valid_chunks_rule_with_remove_seconds():
    # Test valid configuration with remove_seconds
    rule = ChunksRule(
        chunk_size_seconds=10, amount=5, remove_seconds=[(0, 10), (30, 45)]
    )
    assert rule.chunk_size_seconds == 10
    assert rule.amount == 5
    assert rule.remove_seconds == [(0, 10), (30, 45)]


def test_invalid_chunk_size():
    # Chunk size must be > 0
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=0)
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=-5)


def test_invalid_amount():
    # Amount must be >= -1 and cannot be 0
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=10, amount=-2)
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=10, amount=0)


def test_invalid_remove_seconds():
    # Validate each tuple must have length 2, start >= 0, end >= 0, start < end
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=10, remove_seconds=[(10, 5)])  # start > end
    with pytest.raises(ValidationError):
        ChunksRule(chunk_size_seconds=10, remove_seconds=[(-1, 10)])  # start < 0
    with pytest.raises(ValidationError):
        # Tuple must have length 2
        ChunksRule(chunk_size_seconds=10, remove_seconds=[(0, 10, 20)])


def test_rules_config_yaml_parsing(tmp_path):
    # Test parsing valid YAML v3 configuration
    yaml_content = """
    version: 3
    audio_path: "samples/a_ia_ta_ai-1min.wav"
    chunks:
      - chunk_size_seconds: 2
        amount: -1
      - chunk_size_seconds: 10
        amount: 2
        remove_seconds:
          - [0, 10]
          - [30, 40]
    """
    config_file = tmp_path / "rules.yaml"
    config_file.write_text(yaml_content)

    config = load_rules_from_yaml(config_file)
    assert config.version == 3
    assert config.audio_path == "samples/a_ia_ta_ai-1min.wav"
    assert config.output_path == "output"
    assert len(config.chunks) == 2

    assert config.chunks[0].chunk_size_seconds == 2
    assert config.chunks[0].amount == -1
    assert config.chunks[0].remove_seconds is None

    assert config.chunks[1].chunk_size_seconds == 10
    assert config.chunks[1].amount == 2
    assert config.chunks[1].remove_seconds == [(0, 10), (30, 40)]


def test_invalid_yaml_parsing(tmp_path):
    # Test parsing invalid/malformed YAML configuration
    yaml_content = """
    version: 3
    audio_path: "samples/a_ia_ta_ai-1min.wav"
    chunks:
      - chunk_size_seconds: -10
        amount: 2
    """
    config_file = tmp_path / "invalid_rules.yaml"
    config_file.write_text(yaml_content)

    with pytest.raises(ValidationError):
        load_rules_from_yaml(config_file)


def test_invalid_version_yaml_parsing(tmp_path):
    yaml_content = """
    version: 2
    audio_path: "samples/a_ia_ta_ai-1min.wav"
    chunks:
      - chunk_size_seconds: 10
        amount: 2
    """
    config_file = tmp_path / "invalid_version.yaml"
    config_file.write_text(yaml_content)

    with pytest.raises(ValidationError, match="version must be 3"):
        load_rules_from_yaml(config_file)


@pytest.mark.parametrize(
    "bad_audio_path",
    [
        "samples/audio_without_suffix",
        "samples/audio.mp3",
        "samples/audio.flac",
        ".wav",
    ],
)
def test_invalid_audio_path_suffix(tmp_path, bad_audio_path):
    yaml_content = f"""
    version: 3
    audio_path: "{bad_audio_path}"
    chunks:
      - chunk_size_seconds: 10
        amount: 2
    """
    config_file = tmp_path / "invalid_suffix.yaml"
    config_file.write_text(yaml_content)

    with pytest.raises(
        ValidationError, match=r"audio_path must have a '\.wav' or '\.mp4' suffix"
    ):
        load_rules_from_yaml(config_file)
