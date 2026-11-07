import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell
def _():
    from pathlib import Path

    import av
    import typer
    from faster_whisper import WhisperModel

    from audio_samples.utils import decode_audio

    PROJECT_ROOT = Path("/home/antonio/Documents/Python/audio-samples")
    return PROJECT_ROOT, Path, WhisperModel, av, typer


@app.cell
def _(PROJECT_ROOT, Path, typer):
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

    return


@app.cell
def _(WhisperModel):
    model = WhisperModel("base", device="cuda", compute_type="float16")
    return


@app.cell
def _(PROJECT_ROOT, av):
    with av.open(PROJECT_ROOT / "output/samples_agro1/30/13560-13590.wav") as f:
        frames = list(f.decode(audio=0))

    for frame in frames:
        array = frame.to_ndarray()

    array
    return


if __name__ == "__main__":
    app.run()
