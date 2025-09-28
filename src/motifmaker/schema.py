"""Pydantic models that describe the project skeleton."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from pydantic import BaseModel, Field, confloat, conint


class FormSection(BaseModel):
    """A section of the musical form with a basic tension profile."""

    section: str = Field(..., description="Section label such as A, B, or Bridge")
    bars: conint(gt=0) = Field(..., description="Number of bars for the section")
    tension: confloat(ge=0, le=1) = Field(
        ..., description="Normalized tension target for this section"
    )
    motif_label: str = Field(
        "primary",
        description="Which motif variant should be referenced when generating the section",
    )


class ProjectSpec(BaseModel):
    """Full specification for a generated project."""

    form: List[FormSection]
    key: str
    mode: str
    tempo_bpm: conint(gt=20, lt=320)
    meter: str
    style: str
    instrumentation: List[str]
    motif_specs: Dict[str, Dict[str, Any]]


DEFAULT_FORM_TEMPLATE: Dict[str, Sequence[tuple[str, int, float]]] = {
    "ABA": (("A", 8, 0.3), ("B", 8, 0.8), ("A'", 8, 0.4)),
    "AABA": (
        ("A", 8, 0.3),
        ("A", 8, 0.35),
        ("B", 8, 0.8),
        ("A'", 8, 0.4),
    ),
    "ABAB": (("A", 8, 0.3), ("B", 8, 0.7), ("A", 8, 0.4), ("B", 8, 0.75)),
}


def default_from_prompt_meta(meta: Dict[str, Any]) -> ProjectSpec:
    """Construct a :class:`ProjectSpec` from prompt meta information."""

    key = meta.get("key", "C")
    mode = meta.get("mode", "major")
    tempo_bpm = int(meta.get("tempo_bpm", 100))
    meter = meta.get("meter", "4/4")
    style = meta.get("style", "contemporary")
    instrumentation = list(meta.get("instrumentation", ["piano"]))

    form_name = meta.get("form_template", "ABA")
    sections: Sequence[tuple[str, int, float]] = DEFAULT_FORM_TEMPLATE.get(
        form_name,
        DEFAULT_FORM_TEMPLATE["ABA"],
    )

    tension_curve = meta.get("tension_curve")
    form_sections: List[FormSection] = []
    for idx, (label, bars, default_tension) in enumerate(sections):
        tension = default_tension
        if tension_curve and idx < len(tension_curve):
            tension = float(tension_curve[idx])
        form_sections.append(
            FormSection(
                section=label,
                bars=bars,
                tension=max(0.0, min(1.0, tension)),
                motif_label="primary" if label.startswith("A") else "contrast",
            )
        )

    motif_specs = {
        "primary": {
            "contour": meta.get("primary_contour", "ascending-return"),
            "rhythm_density": meta.get("primary_rhythm", "medium"),
        },
        "contrast": {
            "contour": meta.get("contrast_contour", "wave"),
            "rhythm_density": meta.get("contrast_rhythm", "syncopated"),
        },
    }

    return ProjectSpec(
        form=form_sections,
        key=key,
        mode=mode,
        tempo_bpm=tempo_bpm,
        meter=meter,
        style=style,
        instrumentation=instrumentation,
        motif_specs=motif_specs,
    )


__all__ = ["FormSection", "ProjectSpec", "default_from_prompt_meta"]
