"""FastAPI service exposing Motifmaker functionality."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from .parsing import parse_natural_prompt
from .render import render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import ensure_directory

app = FastAPI(title="Motifmaker")


class GenerateRequest(BaseModel):
    """Request model for prompt-based generation."""

    prompt: str


class RenderResponse(BaseModel):
    """Response summarising rendered outputs."""

    output_dir: str
    midi: str
    spec: str
    project: ProjectSpec


@app.post("/generate", response_model=RenderResponse)
async def generate(request: GenerateRequest) -> RenderResponse:
    """Generate a project from a prompt via the API."""

    meta = parse_natural_prompt(request.prompt)
    spec = default_from_prompt_meta(meta)
    output_dir = ensure_directory(Path("outputs") / f"prompt_{uuid4().hex[:8]}")
    midi_path = output_dir / "track.mid"
    json_path = output_dir / "spec.json"
    result = render_project(spec, midi_path, json_path)
    return RenderResponse(
        output_dir=str(output_dir),
        midi=result["midi"],
        spec=result["spec"],
        project=spec,
    )


@app.post("/render", response_model=RenderResponse)
async def render_existing(project: ProjectSpec) -> RenderResponse:
    """Render using an existing project specification."""

    output_dir = ensure_directory(Path("outputs") / f"render_{uuid4().hex[:8]}")
    midi_path = output_dir / "track.mid"
    json_path = output_dir / "spec.json"
    result = render_project(project, midi_path, json_path)
    return RenderResponse(
        output_dir=str(output_dir),
        midi=result["midi"],
        spec=result["spec"],
        project=project,
    )


__all__ = ["app"]
