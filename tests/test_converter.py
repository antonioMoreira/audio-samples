from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

from audio_samples.converter import (
    convert_video_to_wav,
    normalize_video_file,
    normalize_video_name,
    normalize_video_stem,
)


def _create_synthetic_mp4(
    path: Path,
    include_audio: bool = True,
    sample_rate: int = 44100,
    duration_sec: float = 2.0,
) -> Path:
    container = av.open(str(path), mode="w", format="mp4")
    try:
        if include_audio:
            a_stream = container.add_stream("aac", rate=sample_rate)
            a_stream.layout = "stereo"
            a_stream.format = "fltp"
            a_stream.time_base = Fraction(1, sample_rate)

            total_samples = int(sample_rate * duration_sec)
            t = np.linspace(0, duration_sec, total_samples, endpoint=False)
            audio_data = np.sin(2 * np.pi * 440 * t).astype(np.float32)
            stereo_data = np.ascontiguousarray(np.vstack([audio_data, audio_data]))

            frame_size = 1024
            for idx in range(0, total_samples, frame_size):
                chunk = stereo_data[:, idx : idx + frame_size]
                if chunk.shape[1] < frame_size:
                    pad = np.zeros((2, frame_size - chunk.shape[1]), dtype=np.float32)
                    chunk = np.hstack([chunk, pad])
                chunk = np.ascontiguousarray(chunk)
                a_frame = av.AudioFrame.from_ndarray(
                    chunk, format="fltp", layout="stereo"
                )
                a_frame.rate = sample_rate
                a_frame.pts = idx
                a_frame.time_base = Fraction(1, sample_rate)
                for packet in a_stream.encode(a_frame):
                    container.mux(packet)

            for packet in a_stream.encode(None):
                container.mux(packet)
        else:
            # Add a silent video stream
            v_stream = container.add_stream("h264", rate=24)
            v_stream.width = 160
            v_stream.height = 120
            v_stream.pix_fmt = "yuv420p"
            v_stream.time_base = Fraction(1, 24)

            num_v_frames = int(duration_sec * 24)
            for i in range(num_v_frames):
                img = np.zeros((120, 160, 3), dtype=np.uint8)
                v_frame = av.VideoFrame.from_ndarray(img, format="rgb24")
                v_frame.pts = i
                v_frame.time_base = Fraction(1, 24)
                for packet in v_stream.encode(v_frame):
                    container.mux(packet)
            for packet in v_stream.encode(None):
                container.mux(packet)
    finally:
        container.close()

    return path


def test_normalize_video_stem():
    assert normalize_video_stem("This is a video") == "This_is_a_video"
    assert normalize_video_stem("This  is   a video") == "This_is_a_video"
    assert normalize_video_stem("video (1) [HD]") == "video_1_HD"
    assert normalize_video_stem("video@test#1!") == "video_test_1"
    assert normalize_video_stem("already_clean-video") == "already_clean-video"
    assert normalize_video_stem("___") == "video"


def test_normalize_video_name():
    assert normalize_video_name("This is a video.mp4") == "This_is_a_video.mp4"
    assert normalize_video_name(Path("some/dir/My Video (1).mp4")) == "My_Video_1.mp4"


def test_normalize_video_file(tmp_path):
    orig_file = tmp_path / "This is a video.mp4"
    orig_file.write_text("dummy")

    normalized = normalize_video_file(orig_file)
    assert normalized.name == "This_is_a_video.mp4"
    assert normalized.exists()
    assert not orig_file.exists()

    # Calling on already normalized file should be a no-op
    again = normalize_video_file(normalized)
    assert again == normalized
    assert again.exists()


def test_convert_video_to_wav(tmp_path):
    mp4_path = tmp_path / "test_input.mp4"
    _create_synthetic_mp4(
        mp4_path, include_audio=True, sample_rate=44100, duration_sec=2.5
    )

    wav_path = convert_video_to_wav(mp4_path)
    assert wav_path.exists()
    assert wav_path.suffix == ".wav"

    with av.open(str(wav_path)) as container:
        assert len(container.streams.audio) == 1
        stream = container.streams.audio[0]
        assert stream.sample_rate == 16000
        assert stream.channels == 1
        assert stream.format.name == "s16"
        assert stream.codec_context.name == "pcm_s16le"
        assert stream.duration is not None and stream.time_base is not None
        dur = float(stream.duration * stream.time_base)
        assert pytest.approx(dur, 0.1) == 2.5


def test_convert_video_no_audio_raises(tmp_path):
    mp4_path = tmp_path / "silent_video.mp4"
    _create_synthetic_mp4(mp4_path, include_audio=False)

    with pytest.raises(ValueError, match="No audio stream found"):
        convert_video_to_wav(mp4_path)


def test_convert_video_file_not_found():
    with pytest.raises(FileNotFoundError, match="Video file not found"):
        convert_video_to_wav("non_existent_file.mp4")
