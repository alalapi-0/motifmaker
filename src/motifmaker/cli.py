"""Command line interface for the Motifmaker prototype."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from .parsing import parse_natural_prompt
from .render import RenderResult, regenerate_section, render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import configure_logging, ensure_directory

app = typer.Typer(help="Layered music generation prototype")

_LOGGER = logging.getLogger(__name__)

_VALID_STYLES = {"ascending_arc", "wavering", "zigzag"}
_VALID_DENSITIES = {"low", "medium", "high"}
_VALID_HARMONIES = {"basic", "colorful"}


def _validate_choice(
    value: Optional[str], valid: set[str], option_name: str, label: str
) -> Optional[str]:
    """Validate optional CLI choice values.

    Args:
        value: Raw value provided by the user.
        valid: Allowed set of lowercase strings.
        option_name: Option flag used for error提示。

    Returns:
        Normalised lowercase value or ``None``.

    Raises:
        typer.BadParameter: If ``value`` 不在允许的集合内。
    """

    if value is None:
        return None
    normalised = value.lower()
    if normalised not in valid:
        raise typer.BadParameter(
            f"Unsupported {label}: {value}", param_hint=option_name
        )
    return normalised


def _spec_from_prompt(
    prompt: str,
    motif_style: Optional[str],
    rhythm_density: Optional[str],
    harmony_level: Optional[str],
) -> ProjectSpec:
    """Parse the prompt and apply CLI overrides to create a :class:`ProjectSpec`.

    Args:
        prompt: Natural language description provided by the user.
        motif_style: Optional motif style override from CLI flags.
        rhythm_density: Optional rhythm density override.
        harmony_level: Optional harmony complexity override.

    Returns:
        Validated :class:`ProjectSpec` with overrides applied.
    """

    meta = parse_natural_prompt(prompt)
    if motif_style:
        meta["motif_style"] = motif_style
        meta["primary_contour"] = motif_style
    if rhythm_density:
        meta["rhythm_density"] = rhythm_density
        meta["primary_rhythm"] = rhythm_density
    if harmony_level:
        meta["harmony_level"] = harmony_level
    spec = default_from_prompt_meta(meta)
    _LOGGER.debug("Constructed ProjectSpec: %s", spec.model_dump())
    return spec


def _echo_render_result(result: RenderResult) -> None:
    """Print a concise summary of render artefacts.

    Args:
        result: Render outcome returned by :func:`motifmaker.render.render_project`.
    """

    typer.echo(f"Specification saved to: {result['spec']}")
    typer.echo(f"Section summary saved to: {result['summary']}")
    if result["midi"]:
        typer.echo(f"MIDI file saved to: {result['midi']}")
    else:
        typer.echo("MIDI rendering skipped (use --emit-midi to enable).")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable INFO logging"),
    debug: bool = typer.Option(False, "--debug", help="Enable DEBUG logging"),
) -> None:
    """Configure logging switches shared by all commands.

    Args:
        ctx: Typer context used to stash the log level.
        verbose: Flag enabling INFO level logging.
        debug: Flag enabling DEBUG level logging (takes precedence over verbose).
    """

    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    configure_logging(level)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = level


@app.command("init-from-prompt")
def init_from_prompt(
    prompt: str = typer.Argument(..., help="Natural language description of the piece"),
    out: Path = typer.Option(..., help="Output directory"),
    motif_style: Optional[str] = typer.Option(
        None,
        help="Motif style template (ascending_arc|wavering|zigzag)",
    ),
    rhythm_density: Optional[str] = typer.Option(
        None,
        help="Rhythm density control (low|medium|high)",
    ),
    harmony_level: Optional[str] = typer.Option(
        None,
        help="Harmony complexity (basic|colorful)",
    ),
    emit_midi: bool = typer.Option(
        False,
        "--emit-midi/--no-emit-midi",
        help="Write a MIDI file alongside textual outputs",
    ),
) -> None:
    """Generate a project from a natural language prompt.

    Args:
        prompt: Natural language description of the piece.
        out: Directory to write textual outputs.
        motif_style: Optional motif style override.
        rhythm_density: Optional rhythm density override.
        harmony_level: Optional harmony level override.
        emit_midi: Whether to produce a MIDI file.
    """

    try:
        motif_style = _validate_choice(
            motif_style, _VALID_STYLES, "--motif-style", "motif style"
        )
        rhythm_density = _validate_choice(
            rhythm_density, _VALID_DENSITIES, "--rhythm-density", "rhythm density"
        )
        harmony_level = _validate_choice(
            harmony_level, _VALID_HARMONIES, "--harmony-level", "harmony level"
        )
        spec = _spec_from_prompt(prompt, motif_style, rhythm_density, harmony_level)
        output_dir = ensure_directory(out)
        result = render_project(spec, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except Exception as exc:  # pragma: no cover - error path
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


@app.command("render")
def render_from_spec(
    spec_path: Path = typer.Option(
        ..., exists=True, readable=True, help="Specification JSON"
    ),
    out: Path = typer.Option(..., help="Output directory"),
    emit_midi: bool = typer.Option(
        False,
        "--emit-midi/--no-emit-midi",
        help="Write a MIDI file alongside textual outputs",
    ),
) -> None:
    """Render from an existing project specification JSON file.

    Args:
        spec_path: Path to the existing specification JSON.
        out: Output directory for textual artefacts.
        emit_midi: Whether to produce a MIDI file.
    """

    try:
        spec_data = ProjectSpec.model_validate_json(
            spec_path.read_text(encoding="utf-8")
        )
        output_dir = ensure_directory(out)
        result = render_project(spec_data, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except Exception as exc:  # pragma: no cover - error path
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


@app.command("regenerate-section")
def regenerate_section_cmd(
    spec: Path = typer.Option(
        ..., exists=True, readable=True, help="Path to spec.json"
    ),
    section: str = typer.Option(..., help="Section label to regenerate (e.g. B)"),
    out: Path = typer.Option(..., help="Output directory for updated files"),
) -> None:
    """Regenerate a single section and refresh textual artefacts.

    Args:
        spec: Path to ``spec.json`` created by an earlier run.
        section: Section label that should be regenerated.
        out: Directory where the refreshed outputs should be stored.
    """

    try:
        project = ProjectSpec.model_validate_json(spec.read_text(encoding="utf-8"))
        updated_spec, summaries = regenerate_section(project, section)
        output_dir = ensure_directory(out)
        spec_path = output_dir / "spec.json"
        summary_path = output_dir / "summary.txt"
        spec_path.write_text(
            json.dumps(
                updated_spec.model_dump(mode="json"), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        summary_lines = []
        for name, summary in summaries.items():
            chord_summary = ", ".join(summary.get("chords", [])) or "(no harmony)"
            regen_count = summary.get("regeneration_count", 0)
            summary_lines.append(
                f"Section {name} uses motif '{summary.get('motif_label')}' with {summary.get('note_count')} notes and chords: {chord_summary} (regenerated {regen_count} times)"
            )
        summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
        typer.echo(f"Updated spec saved to: {spec_path}")
        typer.echo(f"Summary refreshed at: {summary_path}")
    except Exception as exc:  # pragma: no cover - error path
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
