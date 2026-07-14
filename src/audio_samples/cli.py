import shutil
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError

from audio_samples.feasibility import check_feasibility
from audio_samples.layout_continuous import generate_continuous_layout
from audio_samples.layout_random import generate_random_layout
from audio_samples.loader import load_audio_properties
from audio_samples.rules import load_rules_from_yaml
from audio_samples.writer import slice_audio

DEFAULT_RULES_YAML = Path(__file__).resolve().parent / "default_rule.yaml"

app = typer.Typer(help="Audio Chunks Slicer CLI tool")


@app.command()
def slice_cli(
    config_path: str = typer.Argument(
        str(DEFAULT_RULES_YAML),
        help="Path to the configuration YAML file containing all parameters.",
    ),
):
    rules_path = Path(config_path)
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

    audio_name = config.audio_name
    chunks_dirname = config.chunks_dirname
    sampling_rule = config.sampling_rule
    seed = config.seed

    audio_path = Path(audio_name)
    if not audio_path.is_absolute() and not audio_path.as_posix().startswith(
        "samples/"
    ):
        audio_path = Path("samples") / audio_path

    if (
        audio_path.is_dir() or not audio_path.exists()
    ) and not audio_path.suffix == ".wav":
        wav_path = audio_path.with_suffix(".wav")
        if wav_path.exists() and wav_path.is_file():
            audio_path = wav_path

    if not audio_path.exists():
        typer.echo(f"Error: Audio file not found at {audio_path}", err=True)
        raise typer.Exit(code=1) from None

    if chunks_dirname is None:
        chunks_dirname = audio_path.stem

    output_dir = Path("samples") / chunks_dirname

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
    all_existing_chunks = []

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
                existing_chunks=all_existing_chunks,
            )
            all_existing_chunks.extend(layout)
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
