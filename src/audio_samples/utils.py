"""We use the PyAV library to decode the audio: https://github.com/PyAV-Org/PyAV

The advantage of PyAV is that it bundles the FFmpeg libraries so there is no additional
system dependencies. FFmpeg does not need to be installed on the system.

However, the API is quite low-level so we need to manipulate audio frames directly.
"""

import gc
import io
import itertools
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO, Literal, overload

import av
import numpy as np
import numpy.typing as npt
from av.audio.fifo import AudioFifo
from av.audio.frame import AudioFrame
from av.audio.resampler import AudioResampler

ABS_MIN_INT = abs(np.iinfo(np.int16).min)


@overload
def decode_audio(
    input_file: str | Path | BinaryIO,
    sampling_rate: int = 16000,
    split_stereo: Literal[False] = False,
) -> npt.NDArray[np.float32]: ...


@overload
def decode_audio(
    input_file: str | Path | BinaryIO,
    sampling_rate: int = 16000,
    *,
    split_stereo: Literal[True],
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]: ...


@overload
def decode_audio(
    input_file: str | Path | BinaryIO,
    sampling_rate: int,
    split_stereo: Literal[True],
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]: ...


@overload
def decode_audio(
    input_file: str | Path | BinaryIO,
    sampling_rate: int = 16000,
    split_stereo: bool = False,
) -> (
    npt.NDArray[np.float32] | tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]
): ...


def decode_audio(
    input_file: str | Path | BinaryIO,
    sampling_rate: int = 16000,
    split_stereo: bool = False,
) -> npt.NDArray[np.float32] | tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]:
    """Decodes the audio.

    Args:
      input_file: Path to the input file or a file-like object.
      sampling_rate: Resample the audio to this sample rate.
      split_stereo: Return separate left and right channels.

    Returns:
      A float32 Numpy array.

      If `split_stereo` is enabled, the function returns a 2-tuple with the
      separated left and right channels.
    """
    resampler = AudioResampler(
        format="s16",
        layout="mono" if not split_stereo else "stereo",
        rate=sampling_rate,
    )

    raw_buffer = io.BytesIO()
    dtype = None

    with av.open(input_file, mode="r") as container:
        frames = container.decode(audio=0)
        frames = _ignore_invalid_frames(frames)
        frames = _group_frames(frames, 500_000)
        frames = _resample_frames(frames, resampler)

        for frame in frames:
            array = frame.to_ndarray()
            dtype = array.dtype
            raw_buffer.write(array)

    # It appears that some objects related to the resampler are not freed
    # unless the garbage collector is manually run.
    # https://github.com/SYSTRAN/faster-whisper/issues/390
    # note that this slows down loading the audio a little bit
    # if that is a concern, please use ffmpeg directly as in here:
    # https://github.com/openai/whisper/blob/25639fc/whisper/audio.py#L25-L62
    del resampler
    gc.collect()

    audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype)

    # Convert s16 back to f32.
    audio = audio.astype(np.float32) / ABS_MIN_INT

    if split_stereo:
        left_channel = audio[0::2]
        right_channel = audio[1::2]
        return left_channel, right_channel

    return audio


def _ignore_invalid_frames(frames: Iterable[AudioFrame]) -> Iterator[AudioFrame]:
    iterator = iter(frames)

    while True:
        try:
            yield next(iterator)
        except StopIteration:
            break
        except av.error.InvalidDataError:
            continue


def _group_frames(
    frames: Iterable[AudioFrame], num_samples: int | None = None
) -> Iterator[AudioFrame]:
    fifo = AudioFifo()

    for frame in frames:
        frame.pts = None  # Ignore timestamp check.
        fifo.write(frame)

        if num_samples is not None and fifo.samples >= num_samples:
            out_frame = fifo.read()
            if out_frame is not None:
                yield out_frame

    if fifo.samples > 0:
        out_frame = fifo.read()
        if out_frame is not None:
            yield out_frame


def _resample_frames(
    frames: Iterable[AudioFrame], resampler: AudioResampler
) -> Iterator[AudioFrame]:
    # Add None to flush the resampler.
    for frame in itertools.chain(frames, [None]):
        yield from resampler.resample(frame)


def get_loudness(audio: npt.NDArray[np.float32]) -> float:
    """Calculates the loudness of the audio.

    Args:
      audio: A float32 Numpy array.

    Returns:
      The loudness in dB.
    """
    return 10 * np.log10(np.mean(audio**2) + 1e-10)
