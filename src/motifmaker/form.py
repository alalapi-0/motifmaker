"""Form expansion logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .motif import Motif, MotifNote
from .schema import FormSection, ProjectSpec


@dataclass
class SectionSketch:
    """A simple representation of a section's melodic content."""

    name: str
    notes: List[MotifNote]


def _stretch_motif(motif: Motif, factor: float) -> List[MotifNote]:
    return [
        MotifNote(pitch=note.pitch, duration_beats=note.duration_beats * factor)
        for note in motif.notes
    ]


def _transpose_motif(motif: Motif, semitones: int) -> List[MotifNote]:
    return [
        MotifNote(pitch=note.pitch + semitones, duration_beats=note.duration_beats)
        for note in motif.notes
    ]


def _tail_extend(notes: List[MotifNote], extra_beats: float) -> List[MotifNote]:
    if not notes:
        return []
    extended = list(notes)
    last = extended[-1]
    extended[-1] = MotifNote(
        pitch=last.pitch, duration_beats=last.duration_beats + extra_beats
    )
    return extended


def _motif_variant(motif: Motif, section: FormSection) -> List[MotifNote]:
    if section.section == "A'":
        return _tail_extend(_stretch_motif(motif, 1.0), extra_beats=0.5)
    if section.section.lower().startswith("b"):
        return _transpose_motif(motif, 2)
    if "bridge" in section.section.lower():
        return _stretch_motif(motif, 0.75)
    return motif.notes


def expand_form(spec: ProjectSpec, motifs: Dict[str, Motif]) -> List[SectionSketch]:
    """Expand motifs into section-level melodic sketches."""

    sketches: List[SectionSketch] = []
    for section in spec.form:
        motif = motifs.get(section.motif_label)
        if motif is None:
            raise ValueError(f"Missing motif label: {section.motif_label}")
        notes = _motif_variant(motif, section)

        section_beats = max(1, section.bars) * 4
        motif_beats = max(1.0, motif.total_beats)
        repeats = max(1, int(section_beats // motif_beats))
        aggregated: List[MotifNote] = []
        for _ in range(repeats):
            aggregated.extend(notes)
        if len(aggregated) < 1:
            aggregated.extend(notes)

        sketches.append(SectionSketch(name=section.section, notes=aggregated))
    return sketches


__all__ = ["SectionSketch", "expand_form"]
