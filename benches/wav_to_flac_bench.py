"""Benchmark and lossless verification for WAV -> FLAC -> WAV round-trip using PyAV.

How to Measure Data Loss in PCM-16 WAV -> FLAC -> WAV Conversion
================================================================
FLAC (Free Lossless Audio Codec) compresses integer PCM audio without quantization.
To rigorously verify that converting a `pcm_s16le` WAV file to FLAC and re-converting
it back to `pcm_s16le` WAV (`WAV -> FLAC -> WAV`) introduces zero data loss, we measure
four levels of equivalence across the original WAV signal x[n], the intermediate FLAC
signal y[n], and the re-converted WAV signal z[n]:

1. Stream & Structural Metadata Parity:
   - Sample rate (Hz), channel count, sample format (s16), and total decoded sample
     count N must match identically across all stages: N_wav == N_flac == N_re_wav.

2. Bit-Exact Raw Sample & Cryptographic Hash Equality:
   - Decode all three containers into raw 16-bit signed integer arrays (`np.int16`).
   - Check element-wise equality:
     `np.array_equal(x_int16, y_int16)` and `np.array_equal(x_int16, z_int16)`.
   - Count differing samples: `np.count_nonzero(x_int16 != z_int16) == 0`.
   - Compare SHA-256 digests of the raw decoded PCM byte buffers:
     `sha256(x_int16) == sha256(y_int16) == sha256(z_int16)`.

3. Numerical Reconstruction Error Metrics (in int16 and normalized float32):
   - Maximum Absolute Error (L_inf): max_n |x[n] - z[n]| == 0
   - Mean Absolute Error (MAE):      (1/N) * sum_n |x[n] - z[n]| == 0.0
   - Root Mean Squared Error (RMSE): sqrt((1/N) * sum_n (x[n] - z[n])^2) == 0.0
   - Signal-to-Noise Ratio (SNR):    10 * log10(P_signal / P_error) == +inf dB

4. File Size & Performance Comparison:
   - Original WAV size vs FLAC size vs re-converted WAV size (bytes)
   - Compression ratio (wav_bytes / flac_bytes) and space savings (%)
   - WAV -> FLAC encoding latency and FLAC -> WAV re-conversion latency (ms)
"""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import av
import numpy as np
import numpy.typing as npt
import typer

from audio_samples.utils import decode_audio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "output" / "samples_agro1" / "30"

app = typer.Typer(
    help="Evaluate lossless round-trip conversion (pcm_s16le WAV -> FLAC -> WAV)."
)


@dataclass(frozen=True)
class AudioStreamInfo:
    samples: npt.NDArray[np.int16]
    sample_rate: int
    channels: int
    layout: str
    sample_format: str
    codec_name: str
    sha256: str


@dataclass(frozen=True)
class SignalDiffMetrics:
    num_samples_ref: int
    num_samples_target: int
    mismatched_samples: int
    sha256_match: bool
    bit_exact: bool
    max_abs_error_int16: int
    mae_int16: float
    rmse_int16: float
    max_abs_error_f32: float
    snr_db: float


@dataclass(frozen=True)
class FileComparisonResult:
    filename: str
    wav_bytes: int
    flac_bytes: int
    re_wav_bytes: int
    raw_file_bytes_equal: bool
    sample_rate_match: bool
    channels_match: bool
    sample_format_match: bool
    wav_vs_flac: SignalDiffMetrics
    wav_vs_re_wav: SignalDiffMetrics
    wav_to_flac_ms: float
    flac_to_wav_ms: float
    verify_ms: float

    @property
    def compression_ratio(self) -> float:
        return self.wav_bytes / self.flac_bytes if self.flac_bytes > 0 else 0.0

    @property
    def space_saved_pct(self) -> float:
        if self.wav_bytes == 0:
            return 0.0
        return (1.0 - (self.flac_bytes / self.wav_bytes)) * 100.0

    @property
    def is_flac_lossless(self) -> bool:
        d = self.wav_vs_flac
        return (
            self.sample_rate_match
            and self.channels_match
            and self.sample_format_match
            and d.num_samples_ref == d.num_samples_target
            and d.mismatched_samples == 0
            and d.sha256_match
            and d.bit_exact
            and d.max_abs_error_int16 == 0
            and d.max_abs_error_f32 == 0.0
        )

    @property
    def is_roundtrip_lossless(self) -> bool:
        d = self.wav_vs_re_wav
        return (
            self.is_flac_lossless
            and d.num_samples_ref == d.num_samples_target
            and d.mismatched_samples == 0
            and d.sha256_match
            and d.bit_exact
            and d.max_abs_error_int16 == 0
            and d.max_abs_error_f32 == 0.0
        )


def read_raw_audio_stream(path: Path) -> AudioStreamInfo:
    """Decode raw int16 audio frames and stream metadata from an audio container."""
    chunks: list[npt.NDArray[np.int16]] = []
    with av.open(str(path), mode="r") as container:
        if not container.streams.audio:
            raise ValueError(f"No audio stream found in {path}")
        stream = container.streams.audio[0]
        sample_rate = int(stream.sample_rate or 0)
        channels = int(stream.channels or 0)
        layout = stream.layout.name
        sample_format = stream.format.name if stream.format else "unknown"
        codec_name = stream.codec_context.name

        for frame in container.decode(stream):
            arr = frame.to_ndarray().astype(np.int16, copy=False)
            chunks.append(arr.reshape(-1))

    samples = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.int16)
    digest = hashlib.sha256(samples.tobytes()).hexdigest()
    return AudioStreamInfo(
        samples=samples,
        sample_rate=sample_rate,
        channels=channels,
        layout=layout,
        sample_format=sample_format,
        codec_name=codec_name,
        sha256=digest,
    )


def convert_wav_to_flac(wav_path: Path, flac_path: Path) -> None:
    """Convert a PCM 16-bit WAV file to FLAC using PyAV."""
    with av.open(str(wav_path), mode="r") as in_container:
        if not in_container.streams.audio:
            raise ValueError(f"No audio stream found in {wav_path}")
        in_stream = in_container.streams.audio[0]
        sample_rate = int(in_stream.sample_rate or 16000)
        layout_name = in_stream.layout.name
        format_name = in_stream.format.name if in_stream.format else "s16"

        with av.open(str(flac_path), mode="w", format="flac") as out_container:
            out_stream = out_container.add_stream("flac", rate=sample_rate)
            assert isinstance(out_stream, av.AudioStream)
            out_stream.layout = layout_name
            out_stream.format = format_name

            for frame in in_container.decode(in_stream):
                frame.pts = None
                for packet in out_stream.encode(frame):
                    out_container.mux(packet)

            for packet in out_stream.encode(None):
                out_container.mux(packet)


def convert_flac_to_wav(flac_path: Path, wav_path: Path) -> None:
    """Re-convert a FLAC file back to a PCM 16-bit WAV file using PyAV."""
    with av.open(str(flac_path), mode="r") as in_container:
        if not in_container.streams.audio:
            raise ValueError(f"No audio stream found in {flac_path}")
        in_stream = in_container.streams.audio[0]
        sample_rate = int(in_stream.sample_rate or 16000)
        layout_name = in_stream.layout.name
        format_name = in_stream.format.name if in_stream.format else "s16"

        with av.open(str(wav_path), mode="w", format="wav") as out_container:
            out_stream = out_container.add_stream("pcm_s16le", rate=sample_rate)
            assert isinstance(out_stream, av.AudioStream)
            out_stream.layout = layout_name
            out_stream.format = format_name

            for frame in in_container.decode(in_stream):
                frame.pts = None
                for packet in out_stream.encode(frame):
                    out_container.mux(packet)

            for packet in out_stream.encode(None):
                out_container.mux(packet)


def _compute_signal_diff(
    ref_info: AudioStreamInfo,
    target_info: AudioStreamInfo,
    ref_f32: npt.NDArray[np.float32],
    target_f32: npt.NDArray[np.float32],
) -> SignalDiffMetrics:
    n_ref = int(ref_info.samples.size)
    n_target = int(target_info.samples.size)

    if n_ref == n_target and n_ref > 0:
        diff_i32 = ref_info.samples.astype(np.int32) - target_info.samples.astype(
            np.int32
        )
        abs_diff_i32 = np.abs(diff_i32)
        mismatched = int(np.count_nonzero(diff_i32))
        bit_exact = bool(np.array_equal(ref_info.samples, target_info.samples))
        max_abs_err_i16 = int(np.max(abs_diff_i32))
        mae_i16 = float(np.mean(abs_diff_i32))
        mse_i16 = float(np.mean(diff_i32.astype(np.float64) ** 2))
        rmse_i16 = math.sqrt(mse_i16)

        diff_f32 = np.abs(ref_f32 - target_f32)
        max_abs_err_f32 = float(np.max(diff_f32))

        if mse_i16 == 0.0:
            snr_db = math.inf
        else:
            signal_power = float(
                np.mean(ref_info.samples.astype(np.float64) ** 2)
            )
            snr_db = (
                10.0 * math.log10(signal_power / mse_i16)
                if signal_power > 0.0
                else 0.0
            )
    else:
        mismatched = abs(n_ref - n_target)
        bit_exact = False
        max_abs_err_i16 = 32768
        mae_i16 = math.inf
        rmse_i16 = math.inf
        max_abs_err_f32 = math.inf
        snr_db = -math.inf

    return SignalDiffMetrics(
        num_samples_ref=n_ref,
        num_samples_target=n_target,
        mismatched_samples=mismatched,
        sha256_match=ref_info.sha256 == target_info.sha256,
        bit_exact=bit_exact,
        max_abs_error_int16=max_abs_err_i16,
        mae_int16=mae_i16,
        rmse_int16=rmse_i16,
        max_abs_error_f32=max_abs_err_f32,
        snr_db=snr_db,
    )


def evaluate_file(
    wav_path: Path, flac_path: Path, re_wav_path: Path
) -> FileComparisonResult:
    """Run WAV -> FLAC -> WAV round-trip and compute lossless & size metrics."""
    t0 = time.perf_counter()
    convert_wav_to_flac(wav_path, flac_path)
    wav_to_flac_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    convert_flac_to_wav(flac_path, re_wav_path)
    flac_to_wav_ms = (time.perf_counter() - t1) * 1000.0

    t2 = time.perf_counter()
    wav_info = read_raw_audio_stream(wav_path)
    flac_info = read_raw_audio_stream(flac_path)
    re_wav_info = read_raw_audio_stream(re_wav_path)

    wav_f32 = decode_audio(wav_path, sampling_rate=wav_info.sample_rate)
    flac_f32 = decode_audio(flac_path, sampling_rate=flac_info.sample_rate)
    re_wav_f32 = decode_audio(re_wav_path, sampling_rate=re_wav_info.sample_rate)
    verify_ms = (time.perf_counter() - t2) * 1000.0

    wav_vs_flac = _compute_signal_diff(wav_info, flac_info, wav_f32, flac_f32)
    wav_vs_re_wav = _compute_signal_diff(
        wav_info, re_wav_info, wav_f32, re_wav_f32
    )

    sample_rate_match = (
        wav_info.sample_rate == flac_info.sample_rate == re_wav_info.sample_rate
    )
    channels_match = (
        wav_info.channels == flac_info.channels == re_wav_info.channels
    )
    sample_format_match = (
        wav_info.sample_format
        == flac_info.sample_format
        == re_wav_info.sample_format
    )
    raw_file_bytes_equal = wav_path.read_bytes() == re_wav_path.read_bytes()

    return FileComparisonResult(
        filename=wav_path.name,
        wav_bytes=wav_path.stat().st_size,
        flac_bytes=flac_path.stat().st_size,
        re_wav_bytes=re_wav_path.stat().st_size,
        raw_file_bytes_equal=raw_file_bytes_equal,
        sample_rate_match=sample_rate_match,
        channels_match=channels_match,
        sample_format_match=sample_format_match,
        wav_vs_flac=wav_vs_flac,
        wav_vs_re_wav=wav_vs_re_wav,
        wav_to_flac_ms=wav_to_flac_ms,
        flac_to_wav_ms=flac_to_wav_ms,
        verify_ms=verify_ms,
    )


def _format_bytes(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0 or unit == "GB":
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} GB"


@app.command()
def main(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input-dir",
            "-i",
            help="Directory containing source pcm_s16le .wav files.",
        ),
    ] = DEFAULT_INPUT_DIR,
    max_files: Annotated[
        int,
        typer.Option(
            "--max-files",
            "-n",
            help="Maximum number of WAV files to evaluate (-1 for all files).",
        ),
    ] = 20,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Optional directory to persist .flac and re-converted .wav files.",
        ),
    ] = None,
) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        typer.echo(f"Error: Input directory not found at {input_dir}", err=True)
        raise typer.Exit(code=1)

    wav_files = sorted(input_dir.glob("*.wav"))
    if not wav_files:
        typer.echo(f"Error: No .wav files found in {input_dir}", err=True)
        raise typer.Exit(code=1)

    if max_files > 0:
        wav_files = wav_files[:max_files]

    typer.echo("=" * 106)
    typer.echo(
        "PCM-16 WAV -> FLAC -> WAV Round-Trip Losslessness Benchmark (PyAV)"
    )
    typer.echo("=" * 106)
    typer.echo(
        "\nHow Data Loss Is Measured (WAV -> FLAC and WAV -> FLAC -> WAV):\n"
        "  1. Metadata & Sample Count Parity: "
        "sample_rate, channels, s16 format, N_wav == N_flac == N_re_wav\n"
        "  2. Bit-Exact Raw int16 Check:      "
        "np.array_equal & SHA-256 PCM digest match across all 3 stages\n"
        "  3. Numerical Error Metrics:        "
        "Max Abs Error (int16 & float32), MAE, RMSE, SNR (+inf dB)\n"
        "  4. File Size & Compression Ratio:  "
        "Original .wav vs .flac vs re-converted .wav\n"
    )
    typer.echo(f"Target directory : {input_dir}")
    typer.echo(f"Files evaluated  : {len(wav_files)}")
    typer.echo("-" * 106)
    typer.echo(
        f"{'File':<16} | {'WAV Size':>10} | {'FLAC Size':>10} | {'Re-WAV Size':>11} | "
        f"{'Saved':>6} | {'Ratio':>6} | {'W->F':>6} | {'W->F->W':>7} | "
        f"{'W->F ms':>7} | {'F->W ms':>7}"
    )
    typer.echo("-" * 106)

    results: list[FileComparisonResult] = []

    with tempfile.TemporaryDirectory(prefix="wav2flac_bench_") as tmp_dir_str:
        base_out_dir = output_dir if output_dir is not None else Path(tmp_dir_str)
        flac_dir = base_out_dir / "flac"
        re_wav_dir = base_out_dir / "re_wav"
        flac_dir.mkdir(parents=True, exist_ok=True)
        re_wav_dir.mkdir(parents=True, exist_ok=True)

        for wav_path in wav_files:
            flac_path = flac_dir / f"{wav_path.stem}.flac"
            re_wav_path = re_wav_dir / wav_path.name
            res = evaluate_file(wav_path, flac_path, re_wav_path)
            results.append(res)

            wf_status = "EXACT" if res.is_flac_lossless else "DIFF"
            wfw_status = "EXACT" if res.is_roundtrip_lossless else "DIFF"

            typer.echo(
                f"{res.filename:<16} | "
                f"{_format_bytes(res.wav_bytes):>10} | "
                f"{_format_bytes(res.flac_bytes):>10} | "
                f"{_format_bytes(res.re_wav_bytes):>11} | "
                f"{res.space_saved_pct:>5.1f}% | "
                f"{res.compression_ratio:>5.2f}x | "
                f"{wf_status:>6} | "
                f"{wfw_status:>7} | "
                f"{res.wav_to_flac_ms:>5.1f}ms | "
                f"{res.flac_to_wav_ms:>5.1f}ms"
            )

    total_wav_bytes = sum(r.wav_bytes for r in results)
    total_flac_bytes = sum(r.flac_bytes for r in results)
    total_re_wav_bytes = sum(r.re_wav_bytes for r in results)
    saved_bytes = total_wav_bytes - total_flac_bytes
    overall_saved_pct = (
        (1.0 - (total_flac_bytes / total_wav_bytes)) * 100.0
        if total_wav_bytes > 0
        else 0.0
    )
    overall_ratio = (
        total_wav_bytes / total_flac_bytes if total_flac_bytes > 0 else 0.0
    )
    total_samples = sum(r.wav_vs_flac.num_samples_ref for r in results)
    flac_mismatched = sum(r.wav_vs_flac.mismatched_samples for r in results)
    roundtrip_mismatched = sum(
        r.wav_vs_re_wav.mismatched_samples for r in results
    )
    max_err_flac_i16 = max(r.wav_vs_flac.max_abs_error_int16 for r in results)
    max_err_rt_i16 = max(r.wav_vs_re_wav.max_abs_error_int16 for r in results)
    max_err_rt_f32 = max(r.wav_vs_re_wav.max_abs_error_f32 for r in results)
    exact_container_count = sum(1 for r in results if r.raw_file_bytes_equal)
    all_lossless = all(r.is_roundtrip_lossless for r in results)
    mean_w2f_ms = float(np.mean([r.wav_to_flac_ms for r in results]))
    mean_f2w_ms = float(np.mean([r.flac_to_wav_ms for r in results]))
    verdict = (
        "ZERO DATA LOSS (100% BIT-EXACT WAV -> FLAC -> WAV)"
        if all_lossless
        else "DATA LOSS DETECTED!"
    )

    typer.echo("-" * 106)
    typer.echo("Aggregate Summary:")
    typer.echo(f"  Files evaluated                     : {len(results)}")
    typer.echo(
        f"  Total original WAV size             : "
        f"{_format_bytes(total_wav_bytes)} ({total_wav_bytes:,} bytes)"
    )
    typer.echo(
        f"  Total intermediate FLAC size        : "
        f"{_format_bytes(total_flac_bytes)} ({total_flac_bytes:,} bytes)"
    )
    typer.echo(
        f"  Total re-converted WAV size         : "
        f"{_format_bytes(total_re_wav_bytes)} ({total_re_wav_bytes:,} bytes)"
    )
    typer.echo(
        f"  Exact container file byte matches   : "
        f"{exact_container_count}/{len(results)} files "
        f"(WAV container size diff: {total_re_wav_bytes - total_wav_bytes:+,} bytes)"
    )
    typer.echo(
        f"  FLAC space saved vs WAV             : "
        f"{_format_bytes(saved_bytes)} ({overall_saved_pct:.2f}%, {overall_ratio:.2f}x)"
    )
    typer.echo(f"  Total PCM samples verified          : {total_samples:,}")
    typer.echo(
        f"  Mismatched samples (WAV vs FLAC)    : "
        f"{flac_mismatched} (max abs error int16: {max_err_flac_i16})"
    )
    typer.echo(
        f"  Mismatched samples (WAV vs Re-WAV)  : "
        f"{roundtrip_mismatched} (max abs error int16: {max_err_rt_i16}, "
        f"float32: {max_err_rt_f32:.1f})"
    )
    typer.echo(f"  Mean WAV -> FLAC encode time / file : {mean_w2f_ms:.2f} ms")
    typer.echo(f"  Mean FLAC -> WAV decode time / file : {mean_f2w_ms:.2f} ms")
    typer.echo(f"  Round-Trip Data Loss Verdict        : {verdict}")
    typer.echo("=" * 106)

    if not all_lossless:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
