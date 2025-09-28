"""Motif generation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pretty_midi

SCALE_MAJOR = [0, 2, 4, 5, 7, 9, 11]
SCALE_MINOR = [0, 2, 3, 5, 7, 8, 10]


@dataclass
class MotifNote:
    """Represents a single motif note in beats."""

    pitch: int
    duration_beats: float


@dataclass
class Motif:
    """A short melodic motif."""

    notes: List[MotifNote]

    @property
    def total_beats(self) -> float:
        return sum(note.duration_beats for note in self.notes)


def _scale_for_mode(mode: str) -> List[int]:
    return SCALE_MAJOR if mode == "major" else SCALE_MINOR


def _build_contour(contour: str) -> List[int]:
    if contour == "wave":
        return [0, 2, 5, 2, 0]
    if contour == "descending":
        return [5, 4, 2, 0]
    return [0, 2, 4, 2, 0]


def _durations_for_density(density: str) -> List[float]:
    if density == "syncopated":
        return [0.75, 0.75, 0.5, 1.0]
    if density == "sparse":
        return [1.0, 1.0, 2.0]
    return [0.5, 0.5, 1.0, 1.0]


def generate_motif(spec: dict[str, str | int]) -> Motif:
    """Generate a deterministic motif from a specification."""

    contour = str(spec.get("contour", "ascending-return"))
    density = str(spec.get("rhythm_density", "medium"))
    mode = str(spec.get("mode", "major"))
    root_pitch = int(spec.get("root_pitch", 60))

    contour_steps = _build_contour(contour)
    durations = _durations_for_density(density)

    scale = _scale_for_mode(mode)
    notes: List[MotifNote] = []

    for idx, step in enumerate(contour_steps):
        pitch_offset = scale[int(np.clip(step, 0, len(scale) - 1))]
        pitch = root_pitch + pitch_offset
        duration = durations[idx % len(durations)]
        notes.append(MotifNote(pitch=pitch, duration_beats=duration))

    return Motif(notes=notes)


def motif_to_midi(
    motif: Motif, tempo_bpm: float, program: int = 0
) -> pretty_midi.Instrument:
    """Convert a motif into a PrettyMIDI instrument track."""

    instrument = pretty_midi.Instrument(program=program)
    time = 0.0
    beat_duration = 60.0 / tempo_bpm
    for note in motif.notes:
        start = time
        end = time + note.duration_beats * beat_duration
        instrument.notes.append(
            pretty_midi.Note(velocity=80, pitch=note.pitch, start=start, end=end)
        )
        time = end
    return instrument


__all__ = ["Motif", "MotifNote", "generate_motif", "motif_to_midi"]
