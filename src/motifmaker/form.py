"""Utilities for expanding motifs into longer-form sections.

The form expansion stage takes compact motif definitions and applies a set of
variation operators to produce section-sized melodic sketches.  Each operator
is intentionally lightweight yet expressive enough for unit testing and
textual inspection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

from .motif import Motif, MotifNote
from .schema import FormSection, ProjectSpec

logger = logging.getLogger(__name__)


@dataclass
class SectionSketch:
    """A section-level melodic sketch assembled from motif notes."""

    name: str
    notes: List[MotifNote]


def _stretch_motif(motif: Motif, factor: float) -> List[MotifNote]:
    """Return a time-stretched variant of ``motif``.

    Args:
        motif: Source motif that should be stretched.
        factor: Multiplicative factor applied to each note duration.

    Returns:
        New list of :class:`MotifNote` objects with scaled durations.

    Notes:
        Time stretching implements the "augmentation" variation operator while
        keeping pitches unchanged.
    """

    return [
        MotifNote(pitch=note.pitch, duration_beats=note.duration_beats * factor)
        for note in motif.notes
    ]


def _transpose_motif(motif: Motif, semitones: int) -> List[MotifNote]:
    """Return a transposed copy of ``motif``.

    Args:
        motif: Source motif to transpose.
        semitones: Number of semitones to shift each pitch by.

    Returns:
        List of :class:`MotifNote` with adjusted pitches.
    """

    return [
        MotifNote(pitch=note.pitch + semitones, duration_beats=note.duration_beats)
        for note in motif.notes
    ]


def _tail_extend(notes: List[MotifNote], extra_beats: float) -> List[MotifNote]:
    """Extend the final note to simulate phrase elongation.

    Args:
        notes: Motif notes to augment.
        extra_beats: Additional duration to add to the final note.

    Returns:
        Updated list of notes where only the final note is elongated.
    """

    if not notes:
        return []
    extended = list(notes)
    last = extended[-1]
    extended[-1] = MotifNote(
        pitch=last.pitch, duration_beats=last.duration_beats + extra_beats
    )
    return extended


def _motif_variant(motif: Motif, section: FormSection) -> List[MotifNote]:
    """Select a variation strategy for the section.

    The mapping below loosely mirrors classical development techniques:
    ``A'`` receives a tail extension, ``B`` sections are transposed upward to
    elevate tension, and bridge-like sections are rhythmically compressed.

    Args:
        motif: Motif providing the base material.
        section: Form section describing the structural role.

    Returns:
        List of notes representing the selected variation.
    """

    if section.section == "A'":
        return _tail_extend(_stretch_motif(motif, 1.0), extra_beats=0.5)
    if section.section.lower().startswith("b"):
        return _transpose_motif(motif, 2)
    if "bridge" in section.section.lower():
        return _stretch_motif(motif, 0.75)
    return motif.notes


def expand_form(spec: ProjectSpec, motifs: Dict[str, Motif]) -> List[SectionSketch]:
    """Expand motifs into section-level melodic sketches.

    Args:
        spec: Project specification describing the form structure.
        motifs: Mapping from motif labels to generated motif instances.

    Returns:
        Ordered list of :class:`SectionSketch` objects.

    Raises:
        ValueError: If the specification references an unknown motif label.
    """

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
            # 通过重复动机构建序列化结构，模拟传统曲式中的动机延展。
            aggregated.extend(notes)
        if not aggregated:
            aggregated.extend(notes)

        logger.debug(
            "Expanded section %s with %d notes", section.section, len(aggregated)
        )
        sketches.append(SectionSketch(name=section.section, notes=aggregated))
    return sketches


__all__ = ["SectionSketch", "expand_form"]
