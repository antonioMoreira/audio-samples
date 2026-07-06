import os
import av
from pathlib import Path
from typing import Union


def slice_audio(
    in_path: Union[str, Path],
    out_path: Union[str, Path],
    start_sec: float,
    end_sec: float,
) -> None:
    """Extracts a precise slice from input WAV and writes it to output WAV.

    Args:
        in_path: Path to the input audio file.
        out_path: Path to the output sliced WAV file.
        start_sec: Starting time of the slice in seconds.
        end_sec: Ending time of the slice in seconds.
    """
    in_path_str = str(in_path)
    out_path_str = str(out_path)

    os.makedirs(os.path.dirname(out_path_str), exist_ok=True)

    input_container = av.open(in_path_str)
    try:
        if not input_container.streams.audio:
            raise ValueError("No audio stream found in input file.")
        input_stream = input_container.streams.audio[0]

        sample_rate = input_stream.sample_rate
        codec_name = input_stream.codec_context.name
        layout = input_stream.layout.name
        sample_format = input_stream.format.name

        start_sample = int(start_sec * sample_rate)
        end_sample = int(end_sec * sample_rate)
        total_needed_samples = end_sample - start_sample

        accumulated_bytes = []
        current_sample_idx = 0
        bytes_per_sample_frame = None

        for frame in input_container.decode(audio=0):
            frame_start_sample = current_sample_idx
            frame_end_sample = current_sample_idx + frame.samples
            current_sample_idx += frame.samples

            if bytes_per_sample_frame is None:
                plane = frame.planes[0]
                bytes_per_sample_frame = plane.buffer_size // frame.samples

            overlap_start = max(start_sample, frame_start_sample)
            overlap_end = min(end_sample, frame_end_sample)

            if overlap_start < overlap_end:
                start_offset_samples = overlap_start - frame_start_sample
                end_offset_samples = overlap_end - frame_start_sample

                start_byte = start_offset_samples * bytes_per_sample_frame
                end_byte = end_offset_samples * bytes_per_sample_frame

                mv = memoryview(frame.planes[0])
                accumulated_bytes.append(mv[start_byte:end_byte].tobytes())

            if current_sample_idx >= end_sample:
                break
    finally:
        input_container.close()

    all_bytes = b"".join(accumulated_bytes)

    output_container = av.open(out_path_str, mode="w", format="wav")
    try:
        output_stream = output_container.add_stream(codec_name, rate=sample_rate)
        output_stream.layout = layout
        output_stream.format = sample_format

        write_frame_size = 1024
        total_samples_written = 0

        while total_samples_written < total_needed_samples:
            samples_to_write = min(
                write_frame_size, total_needed_samples - total_samples_written
            )

            out_frame = av.AudioFrame(
                format=sample_format, layout=layout, samples=samples_to_write
            )
            out_frame.sample_rate = sample_rate

            start_byte = total_samples_written * bytes_per_sample_frame
            end_byte = (
                total_samples_written + samples_to_write
            ) * bytes_per_sample_frame
            frame_bytes = all_bytes[start_byte:end_byte]

            out_frame.planes[0].update(frame_bytes)

            out_frame.pts = None
            for packet in output_stream.encode(out_frame):
                output_container.mux(packet)

            total_samples_written += samples_to_write

        for packet in output_stream.encode(None):
            output_container.mux(packet)
    finally:
        output_container.close()
