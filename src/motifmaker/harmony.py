"""Placeholder harmony generation aligning with melodic sketches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .form import SectionSketch
from .schema import ProjectSpec

KEY_TO_MIDI = {
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


HARMONY_PROGRESSIONS = {
    "major": [(0, "I"), (5, "IV"), (7, "V"), (0, "I")],
    "minor": [(0, "i"), (3, "iv"), (7, "V"), (0, "i")],
}


def _triad(root_pitch: int, mode: str, degree: int) -> List[int]:
    scale_intervals = (
        [0, 2, 4, 5, 7, 9, 11] if mode == "major" else [0, 2, 3, 5, 7, 8, 10]
    )
    base = root_pitch + scale_intervals[degree % len(scale_intervals)]
    if mode == "minor" and degree == 4:
        third = base + 4
    else:
        third = base + (4 if mode == "major" or degree in (0, 4) else 3)
    fifth = base + 7
    return [base, third, fifth]


def generate_harmony(
    spec: ProjectSpec, sketches: List[SectionSketch]
) -> Dict[str, List[HarmonyEvent]]:
    """Generate harmony events for each section."""

    root_pitch = KEY_TO_MIDI.get(spec.key, 60)
    progression = HARMONY_PROGRESSIONS.get(spec.mode, HARMONY_PROGRESSIONS["major"])

    harmony: Dict[str, List[HarmonyEvent]] = {}
    for sketch in sketches:
        events: List[HarmonyEvent] = []
        start_beat = 0.0
        total_beats = sum(note.duration_beats for note in sketch.notes)
        segment_beats = 4.0
        idx = 0
        while start_beat < total_beats:
            degree_offset, label = progression[idx % len(progression)]
            degree = (degree_offset // 2) % 7
            pitches = _triad(root_pitch, spec.mode, degree)
            if (
                sketch.name.lower().startswith("b")
                and label.upper() == "V"
                and spec.mode == "minor"
            ):
                pitches = [pitches[0], pitches[0] + 4, pitches[0] + 7]
                pitches[0] = root_pitch + 7
            events.append(
                HarmonyEvent(
                    start_beat=start_beat,
                    duration_beats=segment_beats,
                    chord_name=label,
                    pitches=pitches,
                    bass_pitch=pitches[0] - 12,
                )
            )
            start_beat += segment_beats
            idx += 1
        harmony[sketch.name] = events
    return harmony


__all__ = ["HarmonyEvent", "generate_harmony"]
