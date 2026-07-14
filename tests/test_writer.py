from pathlib import Path

import av
import pytest

from audio_samples.writer import slice_audio


def test_slice_audio_exact_duration(tmp_path):
    in_file = Path("samples/a_ia_ta_ai-1min.wav")
    assert in_file.exists()

    out_file = tmp_path / "slice_5_15.wav"
    slice_audio(in_file, out_file, 5.0, 15.0)

    assert out_file.exists()

    # Read back and verify properties
    with av.open(str(out_file)) as container:
        duration = container.duration
        assert duration is not None
        duration_sec = duration / 1000000.0
        assert pytest.approx(duration_sec, 0.001) == 10.0

        assert len(container.streams.audio) == 1
        stream = container.streams.audio[0]
        assert stream.sample_rate == 16000
        str_dur = stream.duration
        time_base = stream.time_base
        assert str_dur is not None
        assert time_base is not None
        stream_duration = float(str_dur * time_base)
        assert pytest.approx(stream_duration, 0.001) == 10.0


def test_slice_audio_another_range(tmp_path):
    in_file = Path("samples/a_ia_ta_ai-1min.wav")
    out_file = tmp_path / "slice_22_25.wav"

    slice_audio(in_file, out_file, 22.0, 25.0)

    with av.open(str(out_file)) as container:
        duration = container.duration
        assert duration is not None
        duration_sec = duration / 1000000.0
        assert pytest.approx(duration_sec, 0.001) == 3.0
