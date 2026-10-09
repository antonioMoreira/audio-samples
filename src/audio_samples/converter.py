import os
import re
from pathlib import Path

import av


def normalize_video_stem(stem: str) -> str:
    """Normalizes a video filename stem by replacing spaces and special characters.

    Replaces any character that is not alphanumeric, a hyphen, or an underscore
    with an underscore, collapses duplicate underscores, and trims leading/trailing
    underscores.

    Args:
        stem: The stem portion of the filename (without extension).

    Returns:
        The sanitized and normalized stem string.
    """
    normalized = re.sub(r"[^\w\-]+", "_", stem)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized or "video"


def normalize_video_name(filename: str | Path) -> str:
    """Normalizes a video filename (e.g. 'This is video.mp4' -> 'This_is_video.mp4').

    Args:
        filename: Original filename or path.

    Returns:
        The normalized filename preserving its extension.
    """
    path = Path(filename)
    norm_stem = normalize_video_stem(path.stem)
    return f"{norm_stem}{path.suffix}"


def normalize_video_file(video_path: Path) -> Path:
    """Renames a video file on disk if its name contains spaces or special characters.

    Args:
        video_path: Path to the target video file.

    Returns:
        Path to the normalized video file.
    """
    normalized_name = normalize_video_name(video_path.name)
    if video_path.name == normalized_name:
        return video_path

    normalized_path = video_path.with_name(normalized_name)
    if video_path.exists():
        if normalized_path.exists() and normalized_path != video_path:
            normalized_path.unlink()
        video_path.rename(normalized_path)

    return normalized_path


def convert_video_to_wav(
    video_path: str | Path,
    wav_path: str | Path | None = None,
    target_sample_rate: int = 16000,
) -> Path:
    """Converts a video (e.g., MP4) to a 16000 Hz, mono-channel WAV file using PyAV.

    Equivalent to:
        ffmpeg -i [VIDEO].mp4 -ar 16000 -ac 1 [VIDEO].wav

    Args:
        video_path: Path to the input video file.
        wav_path: Optional destination path for the output WAV file. If None,
            uses the video path with a .wav extension.
        target_sample_rate: Desired audio sample rate in Hz (defaults to 16000).

    Returns:
        Path to the generated WAV file.

    Raises:
        FileNotFoundError: If the input video file does not exist.
        ValueError: If no audio stream is found in the video container.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {v_path}")

    if wav_path is None:
        target_wav_path = v_path.with_suffix(".wav")
    else:
        target_wav_path = Path(wav_path)

    os.makedirs(target_wav_path.parent, exist_ok=True)

    in_container = av.open(str(v_path))
    try:
        if not in_container.streams.audio:
            raise ValueError(f"No audio stream found in file: {v_path}")
        in_audio_stream = in_container.streams.audio[0]

        out_container = av.open(str(target_wav_path), mode="w", format="wav")
        try:
            out_stream = out_container.add_stream("pcm_s16le", rate=target_sample_rate)
            out_stream.layout = "mono"
            out_stream.format = "s16"

            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=target_sample_rate,
            )

            for frame in in_container.decode(in_audio_stream):
                for resampled_frame in resampler.resample(frame):
                    for packet in out_stream.encode(resampled_frame):
                        out_container.mux(packet)

            for resampled_frame in resampler.resample(None):
                for packet in out_stream.encode(resampled_frame):
                    out_container.mux(packet)

            for packet in out_stream.encode(None):
                out_container.mux(packet)
        finally:
            out_container.close()
    finally:
        in_container.close()

    return target_wav_path
