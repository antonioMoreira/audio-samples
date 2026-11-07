import shutil
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError

from audio_samples.converter import (
    convert_video_to_wav,
    normalize_video_file,
    normalize_video_name,
)
from audio_samples.feasibility import check_feasibility
from audio_samples.layout_continuous import generate_continuous_layout
from audio_samples.layout_random import generate_random_layout
from audio_samples.loader import load_audio_properties
from audio_samples.rules import load_rules_from_yaml
from audio_samples.writer import slice_audio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

app = typer.Typer(help="Audio Chunks Slicer CLI tool")


@app.command()
def slice_cli(
    config_path: str = typer.Argument(
        ...,
        help="Path to YAML rules configuration file.",
    ),
):
    rules_path = Path(config_path)
    if not rules_path.is_absolute() and not rules_path.exists():
        candidate_rules = PROJECT_ROOT / rules_path
        if candidate_rules.exists():
            rules_path = candidate_rules

    if not rules_path.exists():
        typer.echo(f"Error: YAML rules file not found at {rules_path}", err=True)
        raise typer.Exit(code=1) from None

    try:
        config = load_rules_from_yaml(rules_path)
    except ValidationError as ve:
        typer.echo(f"Validation Error in rules YAML:\n{ve}", err=True)
        raise typer.Exit(code=1) from ve
    except Exception as e:
        typer.echo(f"Error loading YAML rules: {e}", err=True)
        raise typer.Exit(code=1) from e

    chunks_dirname = config.chunks_dirname
    sampling_rule = config.sampling_rule
    seed = config.seed

    audio_path = Path(config.audio_path)
    if not audio_path.is_absolute():
        audio_path = PROJECT_ROOT / audio_path

    if audio_path.suffix.lower() == ".mp4":
        if not audio_path.exists():
            norm_name = normalize_video_name(audio_path.name)
            candidate = audio_path.with_name(norm_name)
            if candidate.exists():
                audio_path = candidate

        if not audio_path.exists() or not audio_path.is_file():
            typer.echo(f"Error: Video file not found at {audio_path}", err=True)
            raise typer.Exit(code=1) from None

        normalized_video = normalize_video_file(audio_path)
        typer.echo(f"Converting video to 16kHz mono WAV: {normalized_video.name}")
        try:
            audio_path = convert_video_to_wav(normalized_video)
        except Exception as e:
            typer.echo(f"Error converting video to WAV: {e}", err=True)
            raise typer.Exit(code=1) from e
        if chunks_dirname is None:
            chunks_dirname = normalized_video.stem
    else:
        if not audio_path.exists() or not audio_path.is_file():
            typer.echo(f"Error: Audio file not found at {audio_path}", err=True)
            raise typer.Exit(code=1) from None

        if chunks_dirname is None:
            chunks_dirname = audio_path.stem

    base_output_dir = Path(config.output_path)
    if not base_output_dir.is_absolute():
        base_output_dir = PROJECT_ROOT / base_output_dir

    output_dir = base_output_dir / chunks_dirname

    try:
        duration, _ = load_audio_properties(audio_path)
    except Exception as e:
        typer.echo(f"Error reading audio metadata: {e}", err=True)
        raise typer.Exit(code=1) from e

    try:
        check_feasibility(
            duration, config.chunks, sampling_rule, remove_seconds=config.remove_seconds
        )
    except ValueError as ve:
        typer.echo(f"Feasibility Error: {ve}", err=True)
        raise typer.Exit(code=1) from ve

    layouts = []
    generated_counts = {}

    for rule in config.chunks:
        rule_sampling_rule = sampling_rule
        if rule_sampling_rule.lower() == "continuous":
            layout = generate_continuous_layout(
                duration, rule, global_remove_seconds=config.remove_seconds
            )
        elif rule_sampling_rule.lower() == "random":
            layout = generate_random_layout(
                duration,
                rule,
                global_remove_seconds=config.remove_seconds,
                seed=seed,
            )
        else:
            typer.echo(f"Error: Unknown sampling rule '{sampling_rule}'", err=True)
            raise typer.Exit(code=1)

        layouts.append((rule, layout))
        generated_counts[rule.chunk_size_seconds] = len(layout)

    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
        except Exception as e:
            typer.echo(f"Error clearing existing chunks directory: {e}", err=True)
            raise typer.Exit(code=1) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Processing audio: {audio_path.name}")
    typer.echo(f"Output directory: {output_dir}")

    for rule, layout in layouts:
        if not layout:
            continue
        size_dir = output_dir / str(rule.chunk_size_seconds)
        size_dir.mkdir(parents=True, exist_ok=True)

        for start, end in layout:
            out_chunk_path = size_dir / f"{start}-{end}.wav"
            try:
                slice_audio(audio_path, out_chunk_path, start, end)
            except Exception as e:
                typer.echo(f"Error writing slice {start}-{end}.wav: {e}", err=True)
                raise typer.Exit(code=1) from e

    output_config = {
        "version": 1,
        "chunks": [
            {"chunk_size_seconds": size, "amount": count}
            for size, count in generated_counts.items()
        ],
    }

    try:
        with open(output_dir / "config.yaml", "w") as f:
            yaml.safe_dump(output_config, f, sort_keys=False)
    except Exception as e:
        typer.echo(f"Error writing output config.yaml: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo("Slicing operation completed successfully!")


if __name__ == "__main__":
    app()
