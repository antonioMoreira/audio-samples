import os
import av
from pathlib import Path
from typing import Tuple, Union


def load_audio_properties(path: Union[str, Path]) -> Tuple[float, int]:
    """Loads the total duration (in seconds) and sample rate of a WAV audio file.

    Args:
        path: Path to the WAV file.

    Returns:
        A tuple of (duration_seconds, sample_rate_hz).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid WAV or has no audio streams.
    """
    path_str = str(path)
    if not os.path.exists(path_str):
        raise FileNotFoundError(f"Audio file not found: {path_str}")

    try:
        container = av.open(path_str)
    except Exception as e:
        raise ValueError(f"Could not open audio file: {e}")

    with container:
        if not container.streams.audio:
            raise ValueError("No audio stream found in the file.")

        stream = container.streams.audio[0]

        duration = None
        if stream.duration is not None and stream.time_base is not None:
            duration = float(stream.duration * stream.time_base)
        elif container.duration is not None:
            duration = container.duration / 1000000.0

        if duration is None:
            raise ValueError("Could not determine audio duration.")

        sample_rate = stream.sample_rate
        if sample_rate is None:
            raise ValueError("Could not determine audio sample rate.")

        return duration, sample_rate
