"""Harmony generation heuristics for Motifmaker.

The module provides a very small rule system that aligns harmony events with
melodic sections.  Two complexity levels are supported: ``basic`` triads and
``colorful`` chords that introduce sevenths or modal mixture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .form import SectionSketch
from .schema import ProjectSpec

logger = logging.getLogger(__name__)

KEY_TO_MIDI: Dict[str, int] = {
    "C": 60,
    "G": 67,
    "D": 62,
    "A": 69,
    "E": 64,
    "F": 65,
    "Bb": 70,
}


@dataclass
class HarmonyEvent:
    """Represents a chord aligned to a time span."""

    start_beat: float
    duration_beats: float
    chord_name: str
    pitches: List[int]
    bass_pitch: int


HARMONY_PROGRESSIONS: Dict[str, Sequence[tuple[int, str]]] = {
    "major": ((0, "I"), (5, "IV"), (7, "V"), (0, "I")),
    "minor": ((0, "i"), (3, "iv"), (7, "V"), (0, "i")),
}


def _scale_degrees(mode: str) -> Sequence[int]:
    """Return scale degrees used for chord building.

    Args:
        mode: Either ``"major"`` or ``"minor"``.

    Returns:
        Sequence of semitone offsets representing the diatonic scale.
    """

    return (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 10)


def _triad(root_pitch: int, mode: str, degree: int) -> List[int]:
    """Construct a simple triad for the given scale degree.

    Args:
        root_pitch: MIDI pitch of the tonic.
        mode: Harmonic mode used for interval selection.
        degree: Scale degree index (0-based).

    Returns:
        List of MIDI pitches forming the triad.
    """

    degrees = _scale_degrees(mode)
    base = root_pitch + degrees[degree % len(degrees)]
    if mode == "minor" and degree == 4:
        third = base + 4
    else:
        third = base + (4 if mode == "major" or degree in (0, 4) else 3)
    fifth = base + 7
    return [base, third, fifth]


def _apply_color(chord: List[int], label: str) -> List[int]:
    """Extend a chord to include sevenths or modal mixture.

    Args:
        chord: Base triad to enrich.
        label: Roman numeral label describing the chord function.

    Returns:
        Extended chord with additional colour tones.
    """

    if label.upper() == "V":
        return chord + [chord[0] + 10]
    if label.lower() == "iv":
        return [chord[0], chord[0] + 5, chord[0] + 8, chord[0] + 12]
    return chord + [chord[0] + 11]


def generate_harmony(
    spec: ProjectSpec, sketches: List[SectionSketch]
) -> Dict[str, List[HarmonyEvent]]:
    """Generate harmony events for each section.

    Args:
        spec: Project specification used to determine key and mode.
        sketches: Section sketches created by :mod:`motifmaker.form`.

    Returns:
        Mapping from section name to ordered :class:`HarmonyEvent` objects.

    Raises:
        ValueError: If a required section is missing (should not happen with
        validated specifications).
    """

    root_pitch = KEY_TO_MIDI.get(spec.key, 60)
    progression = HARMONY_PROGRESSIONS.get(spec.mode, HARMONY_PROGRESSIONS["major"])
    colorful = spec.harmony_level == "colorful"

    harmony: Dict[str, List[HarmonyEvent]] = {}
    for section in sketches:
        events: List[HarmonyEvent] = []
        start_beat = 0.0
        total_beats = sum(note.duration_beats for note in section.notes)
        segment_beats = 4.0
        idx = 0
        while start_beat < total_beats:
            # Iterate through the reference progression in blocks of four beats to
            # loosely mimic functional harmony cycles (tonic → predominant →
            # dominant → tonic).
            degree_offset, label = progression[idx % len(progression)]
            degree = (degree_offset // 2) % 7
            pitches = _triad(root_pitch, spec.mode, degree)
            if colorful:
                # ``colorful`` mode enriches the triad with sevenths or modal
                # mixture to create a denser harmonic field.
                pitches = _apply_color(pitches, label)
            if (
                section.name.lower().startswith("b")
                and label.upper() == "V"
                and spec.mode == "minor"
            ):
                pitches = [pitches[0], pitches[0] + 4, pitches[0] + 7]
                pitches[0] = root_pitch + 7
            events.append(
                HarmonyEvent(
                    start_beat=start_beat,
                    duration_beats=segment_beats,
                    chord_name=label if not colorful else f"{label}7",
                    pitches=pitches,
                    bass_pitch=pitches[0] - 12,
                )
            )
            start_beat += segment_beats
            idx += 1
        harmony[section.name] = events
        logger.debug("Generated %d harmony events for %s", len(events), section.name)
    return harmony


__all__ = ["HarmonyEvent", "generate_harmony", "KEY_TO_MIDI"]
