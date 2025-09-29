"""FastAPI service exposing Motifmaker functionality."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .parsing import parse_natural_prompt
from .render import RenderResult, render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import ensure_directory

logger = logging.getLogger(__name__)

app = FastAPI(title="Motifmaker")


class GenerationOptions(BaseModel):
    """Optional modifiers mirroring the CLI flags."""

    motif_style: Optional[Literal["ascending_arc", "wavering", "zigzag"]] = None
    rhythm_density: Optional[Literal["low", "medium", "high"]] = None
    harmony_level: Optional[Literal["basic", "colorful"]] = None
    emit_midi: bool = False


class GenerateRequest(BaseModel):
    """Request model for prompt-based generation."""

    prompt: str
    options: GenerationOptions | None = None


class RenderResponse(BaseModel):
    """Response summarising rendered outputs."""

    output_dir: str
    spec: str
    summary: str
    midi: str | None
    project: ProjectSpec
    sections: dict[str, dict[str, object]]


def _apply_options(spec: ProjectSpec, options: GenerationOptions | None) -> ProjectSpec:
    """Return a copy of ``spec`` with options merged in.

    Args:
        spec: Base project specification constructed from the prompt.
        options: Optional overrides supplied by the API client.

    Returns:
        A new :class:`ProjectSpec` with overrides applied to the primary motif.
    """

    if not options:
        return spec
    update: dict[str, object] = {}
    motif_specs = dict(spec.motif_specs)
    primary = dict(motif_specs.get("primary", {}))
    if options.motif_style:
        update["motif_style"] = options.motif_style
        primary["motif_style"] = options.motif_style
        primary["contour"] = options.motif_style
    if options.rhythm_density:
        update["rhythm_density"] = options.rhythm_density
        primary["rhythm_density"] = options.rhythm_density
    if options.harmony_level:
        update["harmony_level"] = options.harmony_level
    motif_specs["primary"] = primary
    update["motif_specs"] = motif_specs
    return spec.model_copy(update=update)


def _render_with_paths(spec: ProjectSpec, emit_midi: bool) -> RenderResult:
    """Helper to render a spec into the outputs directory.

    Args:
        spec: Project specification to render.
        emit_midi: Whether a MIDI file should be produced.

    Returns:
        Result dictionary mirroring :func:`motifmaker.render.render_project`.
    """

    output_dir = ensure_directory(Path("outputs") / f"prompt_{uuid4().hex[:8]}")
    logger.info("API rendering into %s (emit_midi=%s)", output_dir, emit_midi)
    return render_project(spec, output_dir, emit_midi=emit_midi)


@app.post("/generate", response_model=RenderResponse)
async def generate(request: GenerateRequest) -> RenderResponse:
    """Generate a project from a prompt via the API."""

    meta = parse_natural_prompt(request.prompt)
    spec = default_from_prompt_meta(meta)
    spec = _apply_options(spec, request.options)
    result = _render_with_paths(
        spec, emit_midi=bool(request.options and request.options.emit_midi)
    )
    return RenderResponse(
        output_dir=result["output_dir"],
        spec=result["spec"],
        summary=result["summary"],
        midi=result["midi"],
        project=spec,
        sections=result["sections"],
    )


class RenderRequest(BaseModel):
    """Request payload for rendering an explicit project specification."""

    project: ProjectSpec
    emit_midi: bool = False


@app.post("/render", response_model=RenderResponse)
async def render_existing(request: RenderRequest) -> RenderResponse:
    """Render using an existing project specification."""

    try:
        result = _render_with_paths(request.project, emit_midi=request.emit_midi)
    except Exception as exc:  # pragma: no cover - FastAPI error path
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RenderResponse(
        output_dir=result["output_dir"],
        spec=result["spec"],
        summary=result["summary"],
        midi=result["midi"],
        project=request.project,
        sections=result["sections"],
    )


__all__ = ["app"]
