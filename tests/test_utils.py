import io
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest
from av.audio.frame import AudioFrame
from av.audio.resampler import AudioResampler

from audio_samples.utils import (
    _group_frames,
    _ignore_invalid_frames,
    _resample_frames,
    decode_audio,
)


def _create_synthetic_wav(
    path: Path,
    sample_rate: int = 16000,
    duration_sec: float = 1.0,
    stereo: bool = False,
) -> Path:
    with av.open(str(path), mode="w", format="wav") as container:
        layout = "stereo" if stereo else "mono"
        stream = container.add_stream("pcm_s16le", rate=sample_rate)
        assert isinstance(stream, av.AudioStream)
        stream.layout = layout
        stream.format = "s16"
        stream.time_base = Fraction(1, sample_rate)

        total_samples = int(sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)
        left = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)

        if stereo:
            right = (np.cos(2 * np.pi * 880 * t) * 8192).astype(np.int16)
            interleaved = np.empty(total_samples * 2, dtype=np.int16)
            interleaved[0::2] = left
            interleaved[1::2] = right
            data = interleaved.reshape(1, -1)
        else:
            data = left.reshape(1, -1)

        data = np.ascontiguousarray(data)
        frame = AudioFrame.from_ndarray(data, format="s16", layout=layout)
        frame.sample_rate = sample_rate
        frame.pts = 0
        frame.time_base = Fraction(1, sample_rate)

        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)

    return path


def test_decode_audio_mono_path_and_str(tmp_path: Path) -> None:
    wav_path = _create_synthetic_wav(
        tmp_path / "mono.wav", sample_rate=16000, duration_sec=1.0, stereo=False
    )

    audio_from_str = decode_audio(str(wav_path), sampling_rate=16000)
    audio_from_path = decode_audio(wav_path, sampling_rate=16000)

    assert isinstance(audio_from_str, np.ndarray)
    assert audio_from_str.dtype == np.float32
    assert audio_from_str.shape == (16000,)
    assert np.all(audio_from_str >= -1.0) and np.all(audio_from_str <= 1.0)
    assert np.array_equal(audio_from_str, audio_from_path)
    assert pytest.approx(float(np.max(np.abs(audio_from_str))), rel=1e-2) == 0.5


def test_decode_audio_binary_io(tmp_path: Path) -> None:
    wav_path = _create_synthetic_wav(
        tmp_path / "mono_io.wav", sample_rate=16000, duration_sec=0.5
    )

    expected = decode_audio(wav_path, sampling_rate=16000)

    with open(wav_path, "rb") as f:
        from_file_obj = decode_audio(f, sampling_rate=16000)

    bytes_io = io.BytesIO(wav_path.read_bytes())
    from_bytes_io = decode_audio(bytes_io, sampling_rate=16000)

    assert np.array_equal(expected, from_file_obj)
    assert np.array_equal(expected, from_bytes_io)


def test_decode_audio_resampling(tmp_path: Path) -> None:
    wav_path = _create_synthetic_wav(
        tmp_path / "resample.wav", sample_rate=44100, duration_sec=1.0
    )

    audio_8k = decode_audio(wav_path, sampling_rate=8000)
    assert audio_8k.dtype == np.float32
    assert abs(audio_8k.shape[0] - 8000) <= 10


def test_decode_audio_split_stereo(tmp_path: Path) -> None:
    wav_path = _create_synthetic_wav(
        tmp_path / "stereo.wav", sample_rate=16000, duration_sec=1.0, stereo=True
    )

    left, right = decode_audio(wav_path, sampling_rate=16000, split_stereo=True)

    assert isinstance(left, np.ndarray)
    assert isinstance(right, np.ndarray)
    assert left.dtype == np.float32
    assert right.dtype == np.float32
    assert left.shape == (16000,)
    assert right.shape == (16000,)
    assert pytest.approx(float(np.max(np.abs(left))), rel=1e-2) == 0.5
    assert pytest.approx(float(np.max(np.abs(right))), rel=1e-2) == 0.25
    assert not np.allclose(left, right)


def test_decode_audio_real_sample() -> None:
    sample_path = Path("samples/a_ia_ta_ai-1min.wav")
    assert sample_path.exists(), f"{sample_path} must exist in workspace"

    audio = decode_audio(sample_path, sampling_rate=16000)
    assert audio.dtype == np.float32
    assert audio.ndim == 1
    assert abs(audio.shape[0] - 60 * 16000) < 1600


def test_ignore_invalid_frames() -> None:
    valid_frame_1 = AudioFrame(format="s16", layout="mono", samples=160)
    valid_frame_2 = AudioFrame(format="s16", layout="mono", samples=160)

    def _frame_generator() -> Iterator[AudioFrame]:
        yield valid_frame_1
        raise av.error.InvalidDataError(1, "corrupted packet")

    class _FaultyIterator:
        def __init__(self) -> None:
            self._step = 0

        def __iter__(self) -> Iterator[AudioFrame]:
            return self

        def __next__(self) -> AudioFrame:
            self._step += 1
            if self._step == 1:
                return valid_frame_1
            if self._step == 2:
                raise av.error.InvalidDataError(1, "invalid frame data")
            if self._step == 3:
                return valid_frame_2
            raise StopIteration

    frames = list(_ignore_invalid_frames(_FaultyIterator()))
    assert frames == [valid_frame_1, valid_frame_2]
    assert list(_ignore_invalid_frames(_frame_generator())) == [valid_frame_1]


def test_group_frames() -> None:
    input_frames = []
    for i in range(5):
        data = np.full((1, 100), i, dtype=np.int16)
        frame = AudioFrame.from_ndarray(data, format="s16", layout="mono")
        frame.sample_rate = 16000
        frame.pts = i * 100
        input_frames.append(frame)

    grouped = list(_group_frames(input_frames, num_samples=250))
    # 100 + 100 + 100 = 300 (>= 250) -> 1st yield (300 samples)
    # 100 + 100 = 200 (remaining > 0) -> 2nd yield (200 samples)
    assert len(grouped) == 2
    assert grouped[0].samples == 300
    assert grouped[1].samples == 200


def test_group_frames_without_limit() -> None:
    input_frames = []
    for _ in range(3):
        data = np.ones((1, 100), dtype=np.int16)
        frame = AudioFrame.from_ndarray(data, format="s16", layout="mono")
        frame.sample_rate = 16000
        input_frames.append(frame)

    grouped = list(_group_frames(input_frames, num_samples=None))
    assert len(grouped) == 1
    assert grouped[0].samples == 300


def test_resample_frames() -> None:
    data = np.zeros((1, 16000), dtype=np.int16)
    frame = AudioFrame.from_ndarray(data, format="s16", layout="mono")
    frame.sample_rate = 16000

    resampler = AudioResampler(format="s16", layout="mono", rate=8000)
    resampled = list(_resample_frames([frame], resampler))

    total_samples = sum(f.samples for f in resampled)
    assert total_samples == 8000
    assert all(f.sample_rate == 8000 for f in resampled)
