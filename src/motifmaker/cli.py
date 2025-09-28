"""Command line interface for the Motifmaker prototype."""

from __future__ import annotations

from pathlib import Path

import typer

from .parsing import parse_natural_prompt
from .render import render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import ensure_directory

app = typer.Typer(help="Layered music generation prototype")


def _spec_from_prompt(prompt: str) -> ProjectSpec:
    meta = parse_natural_prompt(prompt)
    return default_from_prompt_meta(meta)


@app.command("init-from-prompt")
def init_from_prompt(
    prompt: str, out: Path = typer.Option(..., help="Output directory")
) -> None:
    """Generate a project from a natural language prompt."""

    try:
        spec = _spec_from_prompt(prompt)
        output_dir = ensure_directory(out)
        midi_path = output_dir / "track.mid"
        json_path = output_dir / "spec.json"
        result = render_project(spec, midi_path, json_path)
        typer.echo(f"Generated MIDI: {result['midi']}")
        typer.echo(f"Project spec: {result['spec']}")
    except Exception as exc:  # pragma: no cover - error path
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


@app.command("render")
def render_from_spec(
    spec: Path, out: Path = typer.Option(..., help="Output directory")
) -> None:
    """Render from an existing project specification JSON file."""

    try:
        spec_data = ProjectSpec.model_validate_json(spec.read_text())
        output_dir = ensure_directory(out)
        midi_path = output_dir / "track.mid"
        json_path = output_dir / "spec.json"
        result = render_project(spec_data, midi_path, json_path)
        typer.echo(f"Rendered MIDI: {result['midi']}")
        typer.echo(f"Updated spec: {result['spec']}")
    except Exception as exc:  # pragma: no cover - error path
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
