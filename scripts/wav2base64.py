import base64
from pathlib import Path
from typing import Annotated

import pyperclip
import typer

app = typer.Typer(help="Convert WAV files to base64 strings.")


@app.command()
def convert(
    wav_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the WAV file to convert.",
        ),
    ],
    clipboard: Annotated[
        bool,
        typer.Option(
            "--clipboard/--no-clipboard",
            help="Output the base64 string to clipboard using pyperclip.",
        ),
    ] = True,
    print_val: Annotated[
        bool,
        typer.Option(
            "--print/--no-print",
            help="Print the base64 string to stdout.",
        ),
    ] = False,
):
    """Convert a WAV file to a base64 string."""
    if not wav_file.exists():
        typer.echo(f"Error: File not found at {wav_file}", err=True)
        raise typer.Exit(code=1)

    if wav_file.is_dir():
        typer.echo(f"Error: Path is a directory: {wav_file}", err=True)
        raise typer.Exit(code=1)

    try:
        data = wav_file.read_bytes()
        base64_str = base64.b64encode(data).decode("utf-8")

        if clipboard:
            pyperclip.copy(base64_str)

        if print_val:
            typer.echo(base64_str)

    except Exception as e:
        typer.echo(f"Error converting WAV file: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def version():
    """Show the version of wav2base64."""
    typer.echo("wav2base64 version 0.1.0")


if __name__ == "__main__":
    app()
