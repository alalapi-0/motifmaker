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
    """Extend the final note to simulate phrase elongation."""

    if not notes:
        return []
    extended = list(notes)
    last = extended[-1]
    extended[-1] = MotifNote(
        pitch=last.pitch, duration_beats=last.duration_beats + extra_beats
    )
    return extended


def _tail_recycle(notes: List[MotifNote], reduction: float) -> List[MotifNote]:
    """Shorten the final note to produce a clipped release."""

    if not notes:
        return []
    recycled = list(notes)
    last = recycled[-1]
    recycled[-1] = MotifNote(
        pitch=last.pitch, duration_beats=max(0.25, last.duration_beats - reduction)
    )
    return recycled


def _scale_rhythm(notes: List[MotifNote], factor: float) -> List[MotifNote]:
    """Apply a uniform time-scaling factor to the motif."""

    return [
        MotifNote(
            pitch=note.pitch,
            duration_beats=max(0.125, note.duration_beats * factor),
        )
        for note in notes
    ]


def _sequence_expand(notes: List[MotifNote], step: int, repeats: int) -> List[MotifNote]:
    """Create a sequential repetition by transposing the motif."""

    if not notes:
        return []
    expanded: List[MotifNote] = []
    for repeat in range(max(1, repeats)):
        offset = step * repeat
        for note in notes:
            expanded.append(
                MotifNote(pitch=note.pitch + offset, duration_beats=note.duration_beats)
            )
    return expanded


def _motif_variant(motif: Motif, section: FormSection) -> List[MotifNote]:
    """Select a variation strategy for the section using modular operators."""

    label = section.section.upper()
    notes = list(motif.notes)

    if label == "A'":
        pipeline = [
            ("augmentation", {"factor": 1.0}),
            ("tail_extend", {"extra": 0.5}),
        ]
    elif label.startswith("B"):
        pipeline = [
            ("sequence", {"step": 2, "repeats": 2}),
            ("tail_recycle", {"reduction": 0.25}),
        ]
    elif "BRIDGE" in label:
        pipeline = [
            ("diminution", {"factor": 0.75}),
            ("sequence", {"step": 1, "repeats": 2}),
        ]
    elif label == "INTRO":
        pipeline = [
            ("augmentation", {"factor": 1.2}),
            ("tail_recycle", {"reduction": 0.3}),
        ]
    elif label == "OUTRO":
        pipeline = [
            ("augmentation", {"factor": 1.1}),
            ("tail_extend", {"extra": 0.25}),
        ]
    elif label.startswith("C"):
        pipeline = [
            ("sequence", {"step": -2, "repeats": 2}),
            ("diminution", {"factor": 0.9}),
        ]
    else:
        pipeline = []

    for name, params in pipeline:
        if name == "augmentation":
            notes = _scale_rhythm(notes, float(params.get("factor", 1.0)))
        elif name == "diminution":
            notes = _scale_rhythm(notes, float(params.get("factor", 0.75)))
        elif name == "sequence":
            notes = _sequence_expand(
                notes,
                int(params.get("step", 2)),
                int(params.get("repeats", 2)),
            )
        elif name == "tail_extend":
            notes = _tail_extend(notes, float(params.get("extra", 0.5)))
        elif name == "tail_recycle":
            notes = _tail_recycle(notes, float(params.get("reduction", 0.25)))

    if label.startswith("B") and section.section.lower().startswith("b"):
        notes = _transpose_motif(Motif(notes), 2)

    return notes


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
