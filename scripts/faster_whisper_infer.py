import time
from pathlib import Path
from typing import Annotated

import typer
from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = typer.Typer(
    help="Run faster-whisper inference on a WAV file or directory of WAV files."
)


def collect_wav_files(target_path: Path) -> list[Path]:
    """Resolve `target_path` into a sorted list of .wav files."""
    resolved = target_path
    if not resolved.is_absolute() and not resolved.exists():
        candidate = PROJECT_ROOT / resolved
        if candidate.exists():
            resolved = candidate

    if not resolved.exists():
        typer.echo(f"Error: Path not found at {target_path}", err=True)
        raise typer.Exit(code=1)

    if resolved.is_file():
        if resolved.suffix.lower() != ".wav":
            typer.echo(f"Error: Expected a .wav file, got {resolved}", err=True)
            raise typer.Exit(code=1)
        return [resolved]

    wav_files = sorted(resolved.rglob("*.wav"))
    if not wav_files:
        typer.echo(f"Error: No .wav files found in directory {resolved}", err=True)
        raise typer.Exit(code=1)
    return wav_files


@app.command()
def infer(
    audio_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a .wav file or a folder containing multiple .wav files.",
        ),
    ],
    model_size: Annotated[
        str,
        typer.Option("--model", "-m", help="Whisper model size to load."),
    ] = "base",
    device: Annotated[
        str,
        typer.Option(
            "--device", "-d", help="Device to run inference on (cpu, cuda, auto)."
        ),
    ] = "cpu",
    compute_type: Annotated[
        str,
        typer.Option(
            "--compute-type",
            "-c",
            help="Quantization/compute type (int8, float16, default).",
        ),
    ] = "int8",
    language: Annotated[
        str | None,
        typer.Option(
            "--language", "-l", help="Optional language code (e.g. 'pt', 'en')."
        ),
    ] = "pt",
) -> None:
    """Transcribe a WAV file or all WAV files in a directory using faster-whisper."""
    wav_files = collect_wav_files(audio_path)

    typer.echo(
        f"Loading faster-whisper model '{model_size}' "
        f"(device={device}, compute_type={compute_type})..."
    )
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    for wav_file in wav_files:
        typer.echo("-" * 72)
        typer.echo(f"File: {wav_file}")
        t0 = time.perf_counter()
        segments, info = model.transcribe(str(wav_file), beam_size=5, language=language)

        typer.echo(
            f"Detected language: '{info.language}' "
            f"(probability: {info.language_probability:.2f})"
        )
        for segment in segments:
            text = segment.text.strip()
            typer.echo(f"[{segment.start:6.2f}s -> {segment.end:6.2f}s] {text}")

        elapsed = time.perf_counter() - t0
        typer.echo(f"Completed in {elapsed:.2f}s")


if __name__ == "__main__":
    app()
